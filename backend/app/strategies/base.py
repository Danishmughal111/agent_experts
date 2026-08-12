"""Base strategy class — all earning strategies inherit from this."""
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models import EarningStrategy, StrategyExecution, RevenueSource
from app.llm import chat as llm_chat


def dec(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BaseStrategy:
    name: str = "base"
    display_name: str = "Base Strategy"
    risk_level: str = "medium"

    def __init__(self, db: Session):
        self.db = db
        self.config = self._load_config()

    def _load_config(self) -> EarningStrategy:
        cfg = self.db.query(EarningStrategy).filter_by(name=self.name).first()
        if not cfg:
            cfg = EarningStrategy(
                name=self.name,
                display_name=self.display_name,
                risk_level=self.risk_level,
                config_json="{}",
            )
            self.db.add(cfg)
            self.db.commit()
        return cfg

    def is_enabled(self) -> bool:
        return self.config.enabled

    def can_run(self) -> bool:
        """Check if strategy should run (not halted, within limits, etc.)"""
        if not self.is_enabled():
            return False
        from app.agents.finance import check_stop_loss
        sl = check_stop_loss(self.db)
        if sl.get("halted", False):
            return False
        return True

    def log_execution(self, action: str, detail: str = "", result: str = "",
                      profit: float = 0, cost: float = 0,
                      revenue: float = 0, duration: float = 0):
        entry = StrategyExecution(
            strategy_id=self.config.id,
            strategy_name=self.name,
            action=action,
            detail=detail,
            result=result,
            profit=dec(profit),
            cost=dec(cost),
            revenue_generated=dec(revenue),
            duration_seconds=duration,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def record_revenue(self, source_type: str, description: str, amount: float,
                       platform: str = "", external_ref: str = "",
                       currency: str = "USD") -> RevenueSource:
        rev = RevenueSource(
            source_type=source_type,
            description=description,
            amount=dec(amount),
            currency=currency,
            platform=platform,
            external_ref=external_ref,
            settled=False,
        )
        self.db.add(rev)
        self.db.commit()
        return rev

    def ask_ai(self, prompt: str, system: str = "") -> str:
        """Ask the AI (DeepSeek) for reasoning."""
        default_system = (
            "You are a profit-seeking AI business agent. Be practical, "
            "concise, and always consider risk vs reward. Suggest safe, "
            "legal actions that generate real revenue. Reply in clear, "
            "actionable language."
        )
        return llm_chat(prompt, system=system or default_system)

    def run(self) -> dict:
        """Override in subclasses. Returns execution summary dict."""
        raise NotImplementedError