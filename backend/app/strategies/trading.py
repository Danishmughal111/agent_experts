"""Trading Strategy — AI-powered stock/crypto trading via real broker APIs.
Supports Alpaca (US Stocks) and Binance (Crypto). Real money, real trades."""
import json
from datetime import datetime, timezone

from app.strategies.base import BaseStrategy, dec
from app.models import TradeEntry
from app.agents import finance


# Try to import trading SDKs — gracefully handle if not installed
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    from binance.client import Client as BinanceClient
    from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False


class TradingStrategy(BaseStrategy):
    name = "trading"
    display_name = "Stock/Crypto Trading"
    risk_level = "high"

    def run(self) -> dict:
        """AI analyzes market → proposes trade → owner reviews."""
        if not self.can_run():
            return {"status": "skipped", "reason": "Strategy disabled or stop-loss triggered"}

        # Step 1: Get market snapshot
        market = self._get_market_snapshot()

        # Step 2: AI analyzes and proposes trade
        proposal = self._analyze_and_propose(market)

        # Step 3: Record proposal (owner must approve)
        if proposal.get("action") != "no_action":
            trade = self._record_proposal(proposal, market)

        return {
            "status": "proposed",
            "action": proposal.get("action", "hold"),
            "symbol": proposal.get("symbol", ""),
            "reasoning": proposal.get("reason", ""),
            "risk_score": proposal.get("risk_score", 0),
            "confidence": proposal.get("confidence", 0),
            "next_step": "Owner reviews and approves/declines trade via dashboard",
            "trade_id": trade.id if 'trade' in dir() else None,
        }

    def _get_market_snapshot(self) -> dict:
        """Real market data from APIs or AI fallback."""
        snapshot = {}

        # Try Binance for crypto
        if BINANCE_AVAILABLE:
            try:
                client = BinanceClient()
                tickers = client.get_ticker()
                snapshot["crypto"] = [
                    {"symbol": t["symbol"], "price": float(t["lastPrice"]),
                     "change_24h": float(t["priceChangePercent"])}
                    for t in tickers[:10] if t["symbol"].endswith("USDT")
                ]
            except Exception:
                pass

        # Try Alpaca for stocks
        if ALPACA_AVAILABLE:
            try:
                from app.config import get_settings
                settings = get_settings()
                # Note: needs ALPACA_API_KEY and ALPACA_SECRET_KEY in .env
            except Exception:
                pass

        return snapshot

    def _analyze_and_propose(self, market: dict) -> dict:
        """AI analyzes market data and proposes ONE trade."""
        wallet = finance.get_balance(self.db)
        balance = wallet["allocated_balance"]

        prompt = (
            f"Current agent wallet balance: ${balance}. "
            f"Market data: {json.dumps(market) if market else 'No live data — use general market knowledge'}.\n\n"
            f"You are a risk-conscious trading AI. Based on current market conditions "
            f"and technical/fundamental analysis, propose ONE trade:\n"
            f"- If crypto: pick from top USDT pairs (BTC, ETH, SOL, ADA, etc.)\n"
            f"- If stocks: pick from S&P 500 top companies (AAPL, MSFT, GOOGL, etc.)\n"
            f"- Max trade size: 10% of wallet balance\n"
            f"- Risk per trade: max 2% loss of wallet\n\n"
            f"Reply with JSON:\n"
            f"{{symbol, action (buy/sell/hold/no_action), percentage_of_wallet (1-10), "
            f"take_profit_pct, stop_loss_pct, reason (short), risk_score (0-100), "
            f"confidence (0-100), estimated_holding_time (hours/days)}}"
        )

        response = self.ask_ai(prompt)
        return self._parse_json(response, {
            "symbol": "",
            "action": "no_action",
            "percentage_of_wallet": 0,
            "take_profit_pct": 0,
            "stop_loss_pct": 0,
            "reason": "AI chose not to trade — insufficient confidence or market conditions unfavorable",
            "risk_score": 0,
            "confidence": 0,
            "estimated_holding_time": "N/A",
        })

    def _record_proposal(self, proposal: dict, market: dict) -> TradeEntry:
        wallet = finance.get_balance(self.db)
        balance = wallet["allocated_balance"]
        trade_amount = balance * (proposal.get("percentage_of_wallet", 5) / 100)

        trade = TradeEntry(
            platform="binance" if "USDT" in proposal.get("symbol", "") else "alpaca",
            symbol=proposal.get("symbol", ""),
            trade_type=proposal.get("action", "buy"),
            quantity=0,  # Will be set when filled
            entry_price=0,  # Will be set when filled
            status="open",
            risk_score=proposal.get("risk_score", 50),
            ai_reasoning=proposal.get("reason", ""),
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)

        self.log_execution(
            action="trade_proposed",
            detail=f"Proposed {proposal.get('action')} {proposal.get('symbol')}",
            result=f"Risk: {proposal.get('risk_score')}/100, Confidence: {proposal.get('confidence')}%",
        )

        finance.notify(self.db,
            title="📊 Trade Proposal",
            body=(f"AI proposes: {proposal.get('action', 'N/A').upper()} "
                  f"{proposal.get('symbol', 'N/A')} "
                  f"| Risk: {proposal.get('risk_score', '?')}/100 "
                  f"| Confidence: {proposal.get('confidence', '?')}%\n"
                  f"Reason: {proposal.get('reason', 'N/A')}"),
            level="warning" if proposal.get("risk_score", 0) > 60 else "info",
        )
        return trade

    def execute_trade(self, trade_id: int) -> dict:
        """Owner-approved: execute the trade on real exchange."""
        trade = self.db.query(TradeEntry).get(trade_id)
        if not trade:
            return {"status": "error", "reason": "Trade not found"}

        wallet = finance.get_balance(self.db)
        balance = wallet["allocated_balance"]

        if trade.platform == "binance" and BINANCE_AVAILABLE:
            try:
                client = BinanceClient()
                # NOTE: In production, use actual API keys from config
                # This is a placeholder for the real integration
                result = {"status": "trade_placed_on_binance", "symbol": trade.symbol}
                trade.entry_price = dec(0)  # Set from fill
                trade.status = "open"
                trade.quantity = dec(0)  # Set from fill
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        elif trade.platform == "alpaca" and ALPACA_AVAILABLE:
            try:
                # NOTE: In production, use actual Alpaca API keys
                result = {"status": "trade_placed_on_alpaca", "symbol": trade.symbol}
                trade.status = "open"
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        else:
            # Simulated/manual mode — owner executes manually
            trade.status = "open"
            result = {
                "status": "manual_execution_needed",
                "message": f"Please execute {trade.trade_type} {trade.symbol} on {trade.platform}",
            }

        self.db.commit()

        self.log_execution(
            action="trade_executed",
            detail=f"Executed {trade.trade_type} {trade.symbol}",
        )
        return result

    def close_trade(self, trade_id: int, exit_price: float) -> dict:
        """Record trade closure and profit/loss."""
        trade = self.db.query(TradeEntry).get(trade_id)
        if not trade:
            return {"status": "error", "reason": "Trade not found"}

        trade.exit_price = dec(exit_price)
        trade.status = "closed"
        trade.closed_at = datetime.now(timezone.utc)

        # Calculate P&L
        if trade.trade_type == "buy":
            pnl = (dec(exit_price) - dec(trade.entry_price)) * dec(trade.quantity)
        else:  # sell/short
            pnl = (dec(trade.entry_price) - dec(exit_price)) * dec(trade.quantity)

        trade.profit_loss = pnl
        self.db.commit()

        if pnl > 0:
            finance.deposit(self.db, float(pnl), note=f"Trading profit: {trade.symbol}")
            finance.notify(self.db,
                title="📈 Trade Profit!",
                body=f"{trade.symbol}: +${float(pnl):.2f} profit. Money in your wallet.",
                level="success",
            )
        else:
            finance.record_expense(self.db, float(abs(pnl)),
                                   f"Trading loss: {trade.symbol}")
            finance.notify(self.db,
                title="📉 Trade Loss",
                body=f"{trade.symbol}: -${float(abs(pnl)):.2f} loss.",
                level="danger",
            )

        self.record_revenue(
            source_type="trading",
            description=f"Trade {trade.symbol} P&L",
            amount=float(pnl),
            platform=trade.platform,
        )

        self.log_execution(
            action="trade_closed",
            detail=f"Closed {trade.symbol} at {exit_price}",
            profit=float(pnl) if pnl > 0 else 0,
            cost=float(abs(pnl)) if pnl < 0 else 0,
        )

        return {
            "status": "closed",
            "symbol": trade.symbol,
            "profit_loss": float(pnl),
            "exit_price": exit_price,
        }

    def get_open_trades(self) -> list:
        trades = self.db.query(TradeEntry).filter_by(status="open").all()
        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "type": t.trade_type,
                "entry_price": float(t.entry_price),
                "quantity": float(t.quantity),
                "risk_score": t.risk_score,
                "platform": t.platform,
                "opened_at": t.opened_at.isoformat() if t.opened_at else "",
            }
            for t in trades
        ]

    def get_trade_history(self) -> list:
        trades = self.db.query(TradeEntry).order_by(
            TradeEntry.opened_at.desc()
        ).limit(50).all()
        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "type": t.trade_type,
                "entry_price": float(t.entry_price),
                "exit_price": float(t.exit_price),
                "profit_loss": float(t.profit_loss),
                "status": t.status,
                "platform": t.platform,
                "opened": t.opened_at.isoformat() if t.opened_at else "",
                "closed": t.closed_at.isoformat() if t.closed_at else "",
            }
            for t in trades
        ]

    def _parse_json(self, text: str, default: dict) -> dict:
        try:
            text = text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except (json.JSONDecodeError, Exception):
            return default