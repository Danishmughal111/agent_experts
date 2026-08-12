"""Main Decision Engine — AI chooses which strategy to run based on market conditions,
risk/reward analysis, and current portfolio state."""
import json
import time
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.strategies.base import BaseStrategy, dec
from app.models import EarningStrategy, StrategyExecution
from app.agents import finance
from app.llm import chat as llm_chat


DECISION_SYSTEM = (
    "You are an AI decision engine. Your job is to analyze the current financial "
    "situation and pick the single best earning strategy to execute RIGHT NOW. "
    "Consider: current wallet balance, market conditions, risk tolerance, "
    "time of day, and which strategy has highest probability of real profit. "
    "Be decisive. Reply with ONLY a JSON object with these keys: "
    "strategy (one of: digital_products, coding_agent, content, trading, freelance, business), "
    "reason (short why), confidence (0-100), expected_profit_usd (estimate), risk_level (low/medium/high)."
)


STRATEGY_DEFAULTS = {
    "digital_products": {"display": "Digital Products (Gumroad)", "risk": "low"},
    "coding_agent": {"display": "AI Coding Agent", "risk": "medium"},
    "content": {"display": "Content Monetization", "risk": "low"},
    "trading": {"display": "Stock/Crypto Trading", "risk": "high"},
    "freelance": {"display": "Freelance Bot", "risk": "medium"},
    "business": {"display": "Business Website & Agent", "risk": "low"},
}


def ensure_default_strategies(db: Session):
    """Create default earning strategies if they don't exist."""
    for name, cfg in STRATEGY_DEFAULTS.items():
        existing = db.query(EarningStrategy).filter_by(name=name).first()
        if not existing:
            db.add(EarningStrategy(
                name=name,
                display_name=cfg["display"],
                risk_level=cfg["risk"],
                daily_profit_target=Decimal("50.00"),
                daily_loss_limit=Decimal("20.00"),
                max_concurrent=5,
                config_json="{}",
            ))
    db.commit()


class Scheduler:
    """Orchestrates all earning strategies. AI-powered decision loop."""

    STRATEGY_NAMES = list(STRATEGY_DEFAULTS.keys())

    def __init__(self, db: Session):
        self.db = db
        ensure_default_strategies(db)

    def _ensure_strategies_exist(self):
        ensure_default_strategies(self.db)

    def get_current_state(self) -> dict:
        """Snapshot of current financial state for AI decision."""
        wallet = finance.get_balance(self.db)
        sl = finance.check_stop_loss(self.db)
        strategies = self.db.query(EarningStrategy).all()
        return {
            "wallet_balance": wallet["allocated_balance"],
            "currency": wallet["currency"],
            "stop_loss_halted": sl["halted"],
            "stop_loss_reason": sl.get("reason", ""),
            "active_strategies": [
                {"name": s.name, "enabled": s.enabled, "risk": s.risk_level}
                for s in strategies if s.enabled
            ],
            "time_utc": datetime.now(timezone.utc).isoformat(),
        }

    def decide(self) -> dict:
        """AI picks the best strategy to run right now."""
        state = self.get_current_state()

        if state["stop_loss_halted"]:
            return {
                "strategy": None,
                "reason": f"Stop-loss halted: {state['stop_loss_reason']}",
                "confidence": 0,
                "expected_profit_usd": 0,
                "risk_level": "none",
            }

        if not state["active_strategies"]:
            return {
                "strategy": None,
                "reason": "No active strategies enabled",
                "confidence": 0,
                "expected_profit_usd": 0,
                "risk_level": "none",
            }

        prompt = (
            f"Current wallet: ${state['wallet_balance']} {state['currency']}. "
            f"Time: {state['time_utc']}. "
            f"Enabled strategies: {json.dumps(state['active_strategies'])}. "
            f"Money goes to owner's Payoneer account. Pick the best strategy to execute now."
        )

        try:
            response = llm_chat(prompt, system=DECISION_SYSTEM)
            # Try to extract JSON from response
            response = response.strip()
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            decision = json.loads(response)
        except (json.JSONDecodeError, Exception):
            # Fallback: pick lowest risk enabled strategy
            enabled = state["active_strategies"]
            low_risk = [s for s in enabled if s["risk"] == "low"]
            pick = low_risk[0] if low_risk else enabled[0]
            decision = {
                "strategy": pick["name"],
                "reason": "Fallback — lowest risk active strategy",
                "confidence": 50,
                "expected_profit_usd": 5,
                "risk_level": pick["risk"],
            }

        return decision

    def run_cycle(self) -> dict:
        """Execute one full cycle: decide → execute → log."""
        start = time.time()

        decision = self.decide()
        strategy_name = decision.get("strategy")

        if not strategy_name:
            return {
                "status": "skipped",
                "reason": decision.get("reason", "No strategy chosen"),
                "decision": decision,
            }

        # Import and instantiate the chosen strategy
        strategy = self._get_strategy(strategy_name)
        if not strategy:
            return {
                "status": "error",
                "reason": f"Strategy '{strategy_name}' not found",
                "decision": decision,
            }

        if not strategy.can_run():
            return {
                "status": "skipped",
                "reason": f"Strategy '{strategy_name}' cannot run (disabled or stop-loss)",
                "decision": decision,
            }

        try:
            result = strategy.run()
            duration = time.time() - start
            result["decision"] = decision
            result["duration_seconds"] = round(duration, 2)

            strategy.log_execution(
                action="cycle_completed" if result.get("status") == "completed" else "cycle_run",
                detail=json.dumps(decision),
                result=json.dumps(result, default=str),
                revenue=float(result.get("revenue", result.get("profit", 0))),
                duration=duration,
            )
            return result
        except Exception as e:
            duration = time.time() - start
            strategy.log_execution(
                action="cycle_failed",
                detail=str(e),
                duration=duration,
            )
            return {
                "status": "failed",
                "strategy": strategy_name,
                "error": str(e),
                "decision": decision,
                "duration_seconds": round(duration, 2),
            }

    def _get_strategy(self, name: str) -> BaseStrategy:
        """Lazy-import and instantiate a strategy by name."""
        from app.strategies.digital_products import DigitalProductsStrategy
        from app.strategies.coding_agent import CodingAgentStrategy
        from app.strategies.content import ContentStrategy
        from app.strategies.trading import TradingStrategy
        from app.strategies.freelance import FreelanceStrategy
        from app.strategies.business import BusinessStrategy

        mapping = {
            "digital_products": DigitalProductsStrategy,
            "coding_agent": CodingAgentStrategy,
            "content": ContentStrategy,
            "trading": TradingStrategy,
            "freelance": FreelanceStrategy,
            "business": BusinessStrategy,
        }
        cls = mapping.get(name)
        if cls:
            return cls(self.db)
        return None

    def run_all_enabled(self) -> list:
        """Run all enabled strategies (not just one). For aggressive earning mode."""
        results = []
        for name in self.STRATEGY_NAMES:
            strategy = self._get_strategy(name)
            if strategy and strategy.can_run():
                try:
                    result = strategy.run()
                    results.append({"strategy": name, **result})
                except Exception as e:
                    results.append({"strategy": name, "status": "failed", "error": str(e)})
        return results