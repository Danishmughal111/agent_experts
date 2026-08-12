"""API routes for the AI Earning Machine — all 7 strategies + scheduler + Payoneer."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.auth import verify_owner, verify_agent_token
from app.db import SessionLocal
from app.strategies.scheduler import Scheduler, ensure_default_strategies
from app.strategies.digital_products import DigitalProductsStrategy
from app.strategies.coding_agent import CodingAgentStrategy
from app.strategies.content import ContentStrategy
from app.strategies.trading import TradingStrategy
from app.strategies.freelance import FreelanceStrategy
from app.strategies.business import BusinessStrategy
from app.models import (
    EarningStrategy, StrategyExecution, RevenueSource,
    PayoneerTransaction, DigitalProduct, CodingProject,
    PublishedContent, TradeEntry, FreelanceLead,
    BusinessDeal, WebsiteInstance,
)
from app.agents import finance

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== SCHEDULER (Decision Engine) ====================

class RunCycleResponse(BaseModel):
    status: str
    reason: Optional[str] = None
    detail: Optional[str] = None


@router.post("/strategies/run-cycle")
def run_strategy_cycle(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        scheduler = Scheduler(db)
        result = scheduler.run_cycle()
        return result
    finally:
        db.close()


@router.post("/strategies/run-all")
def run_all_strategies(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        scheduler = Scheduler(db)
        results = scheduler.run_all_enabled()
        return {"strategies_run": len(results), "results": results}
    finally:
        db.close()


@router.get("/strategies/decide")
def get_ai_decision(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        scheduler = Scheduler(db)
        return scheduler.decide()
    finally:
        db.close()


@router.get("/strategies")
def list_strategies(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        ensure_default_strategies(db)
        strategies = db.query(EarningStrategy).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "display_name": s.display_name,
                "enabled": s.enabled,
                "risk_level": s.risk_level,
                "daily_profit_target": float(s.daily_profit_target),
                "daily_loss_limit": float(s.daily_loss_limit),
            }
            for s in strategies
        ]
    finally:
        db.close()


class ToggleStrategyIn(BaseModel):
    enabled: bool


@router.post("/strategies/{name}/toggle")
def toggle_strategy(name: str, body: ToggleStrategyIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        s = db.query(EarningStrategy).filter_by(name=name).first()
        if not s:
            raise HTTPException(404, "Strategy not found")
        s.enabled = body.enabled
        db.commit()
        return {"name": name, "enabled": s.enabled}
    finally:
        db.close()


@router.get("/strategies/executions")
def strategy_executions(limit: int = 50, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        rows = db.query(StrategyExecution).order_by(
            StrategyExecution.created_at.desc()
        ).limit(limit).all()
        return [
            {
                "id": r.id,
                "strategy": r.strategy_name,
                "action": r.action,
                "detail": r.detail,
                "result": r.result,
                "profit": float(r.profit),
                "cost": float(r.cost),
                "revenue": float(r.revenue_generated),
                "duration": r.duration_seconds,
                "time": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


# ==================== DIGITAL PRODUCTS (Gumroad) ====================

@router.get("/digital-products")
def list_products(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = DigitalProductsStrategy(db)
        return strat.get_all_products()
    finally:
        db.close()


class ProductSaleIn(BaseModel):
    product_id: int
    amount: float
    gumroad_ref: str = ""


@router.post("/digital-products/record-sale")
def record_product_sale(body: ProductSaleIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = DigitalProductsStrategy(db)
        return strat.record_sale(body.product_id, body.amount, body.gumroad_ref)
    finally:
        db.close()


# ==================== CODING AGENT ====================

@router.get("/coding-projects")
def list_coding_projects(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = CodingAgentStrategy(db)
        return strat.get_all_projects()
    finally:
        db.close()


class CodingPaymentIn(BaseModel):
    project_id: int
    amount: float
    client_name: str
    payoneer_ref: str = ""


@router.post("/coding-projects/record-payment")
def record_coding_payment(body: CodingPaymentIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = CodingAgentStrategy(db)
        return strat.record_client_payment(
            body.project_id, body.amount,
            body.client_name, body.payoneer_ref,
        )
    finally:
        db.close()


# ==================== CONTENT ====================

@router.get("/content")
def list_content(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = ContentStrategy(db)
        return strat.get_all_content()
    finally:
        db.close()


class ContentRevenueIn(BaseModel):
    content_id: int
    amount: float
    source: str = ""


@router.post("/content/record-revenue")
def record_content_revenue(body: ContentRevenueIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = ContentStrategy(db)
        return strat.record_revenue_from_content(
            body.content_id, body.amount, body.source,
        )
    finally:
        db.close()


# ==================== TRADING ====================

@router.get("/trades")
def list_trades(status: str = "", _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = TradingStrategy(db)
        if status == "open":
            return strat.get_open_trades()
        return strat.get_trade_history()
    finally:
        db.close()


class ExecuteTradeIn(BaseModel):
    trade_id: int


@router.post("/trades/execute")
def execute_trade(body: ExecuteTradeIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = TradingStrategy(db)
        return strat.execute_trade(body.trade_id)
    finally:
        db.close()


class CloseTradeIn(BaseModel):
    trade_id: int
    exit_price: float


@router.post("/trades/close")
def close_trade(body: CloseTradeIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = TradingStrategy(db)
        return strat.close_trade(body.trade_id, body.exit_price)
    finally:
        db.close()


# ==================== FREELANCE ====================

@router.get("/freelance-leads")
def list_freelance_leads(status: str = "", _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = FreelanceStrategy(db)
        return strat.get_leads(status=status)
    finally:
        db.close()


class LeadActionIn(BaseModel):
    lead_id: int
    external_ref: str = ""


@router.post("/freelance-leads/mark-applied")
def mark_lead_applied(body: LeadActionIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = FreelanceStrategy(db)
        return strat.mark_applied(body.lead_id, body.external_ref)
    finally:
        db.close()


class LeadAcceptIn(BaseModel):
    lead_id: int
    agreed_amount: float = None


@router.post("/freelance-leads/mark-accepted")
def mark_lead_accepted(body: LeadAcceptIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = FreelanceStrategy(db)
        return strat.mark_accepted(body.lead_id, body.agreed_amount)
    finally:
        db.close()


class FreelancePaymentIn(BaseModel):
    lead_id: int
    amount: float
    client_name: str = ""
    payoneer_ref: str = ""


@router.post("/freelance-leads/record-payment")
def record_freelance_payment(body: FreelancePaymentIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = FreelanceStrategy(db)
        return strat.record_payment(
            body.lead_id, body.amount,
            body.client_name, body.payoneer_ref,
        )
    finally:
        db.close()


# ==================== BUSINESS ====================

@router.get("/business-deals")
def list_business_deals(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = BusinessStrategy(db)
        return strat.get_pipeline()
    finally:
        db.close()


class DealStatusIn(BaseModel):
    deal_id: int
    new_status: str


@router.post("/business-deals/update-status")
def update_deal_status(body: DealStatusIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = BusinessStrategy(db)
        return strat.update_deal_status(body.deal_id, body.new_status)
    finally:
        db.close()


class BusinessPaymentIn(BaseModel):
    deal_id: int
    amount_received: float
    payoneer_ref: str = ""


@router.post("/business-deals/record-payment")
def record_business_payment(body: BusinessPaymentIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = BusinessStrategy(db)
        return strat.close_won_deal(
            body.deal_id, body.amount_received, body.payoneer_ref,
        )
    finally:
        db.close()


class ColdEmailIn(BaseModel):
    lead_name: str
    company: str
    service: str


@router.post("/business/generate-email")
def generate_cold_email(body: ColdEmailIn, _=Depends(verify_owner)):
    db = SessionLocal()
    try:
        strat = BusinessStrategy(db)
        return {"email": strat.generate_cold_email(
            body.lead_name, body.company, body.service,
        )}
    finally:
        db.close()


# ==================== REVENUE TRACKING ====================

@router.get("/revenue")
def list_revenue(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        rows = db.query(RevenueSource).order_by(
            RevenueSource.created_at.desc()
        ).limit(100).all()
        return [
            {
                "id": r.id,
                "source_type": r.source_type,
                "description": r.description,
                "amount": float(r.amount),
                "currency": r.currency,
                "platform": r.platform,
                "settled": r.settled,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


# ==================== PAYONEER WEBHOOK ====================

class PayoneerWebhookIn(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "USD"
    payer_name: str = ""
    source_type: str = ""
    raw_data: str = ""


@router.post("/payoneer/webhook")
def payoneer_webhook(body: PayoneerWebhookIn):
    """Receive Payoneer payment notifications and update ledger."""
    db = SessionLocal()
    try:
        txn = PayoneerTransaction(
            external_ref=body.transaction_id,
            amount=body.amount,
            currency=body.currency,
            payer_name=body.payer_name,
            source_type=body.source_type,
            status="confirmed",
            raw_data=body.raw_data,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        # Credit agent wallet
        finance.deposit(db, body.amount,
                        note=f"Payoneer payment from {body.payer_name}: {body.source_type}")
        finance.notify(db,
            title="💵 Payoneer Payment Received!",
            body=f"${body.amount} from {body.payer_name} ({body.source_type}). Check your Payoneer account.",
            level="success",
        )

        return {"status": "recorded", "transaction_id": txn.external_ref}
    finally:
        db.close()


@router.get("/payoneer/transactions")
def list_payoneer_txns(_=Depends(verify_owner)):
    db = SessionLocal()
    try:
        txns = db.query(PayoneerTransaction).order_by(
            PayoneerTransaction.created_at.desc()
        ).limit(50).all()
        return [
            {
                "id": t.id,
                "ref": t.external_ref,
                "amount": float(t.amount),
                "currency": t.currency,
                "payer": t.payer_name,
                "source": t.source_type,
                "status": t.status,
                "time": t.created_at.isoformat(),
            }
            for t in txns
        ]
    finally:
        db.close()


# ==================== AGENT ACTIVITY LOGS ====================

@router.get("/agent/logs")
def agent_logs(limit: int = 100, _=Depends(verify_owner)):
    """Combined activity feed: what the agent is doing right now + history."""
    from sqlalchemy import desc
    from app.models import AgentTask

    db = SessionLocal()
    try:
        ensure_default_strategies(db)

        # Agent tasks (chat + autonomous actions)
        tasks = db.query(AgentTask).order_by(desc(AgentTask.created_at)).limit(limit).all()

        # Strategy executions
        executions = db.query(StrategyExecution).order_by(
            desc(StrategyExecution.created_at)).limit(limit).all()

        # Notifications
        from app.models import Notification
        notifications = db.query(Notification).order_by(
            desc(Notification.created_at)).limit(limit).all()

        feed = []

        for t in tasks:
            feed.append({
                "type": "agent_action" if t.action != "chat" else "chat",
                "source": "agent",
                "action": t.action,
                "detail": t.detail,
                "result": t.result,
                "time": t.created_at.isoformat(),
            })

        for e in executions:
            feed.append({
                "type": "strategy",
                "source": "strategy",
                "action": e.action,
                "detail": e.detail,
                "result": e.result,
                "revenue": float(e.revenue_generated),
                "profit": float(e.profit),
                "time": e.created_at.isoformat(),
            })

        for n in notifications:
            feed.append({
                "type": "notification",
                "source": "notification",
                "action": n.title,
                "detail": n.body,
                "level": n.level,
                "time": n.created_at.isoformat(),
            })

        # Sort by time (newest first)
        feed.sort(key=lambda x: x.get("time", ""), reverse=True)
        return feed[:limit]
    finally:
        db.close()


# ==================== DASHBOARD SUMMARY ====================

@router.get("/dashboard/summary")
def dashboard_summary(_=Depends(verify_owner)):
    """Aggregated view of all earnings for the frontend."""
    db = SessionLocal()
    try:
        ensure_default_strategies(db)
        wallet = finance.get_balance(db)
        sl = finance.check_stop_loss(db)

        # Revenue totals
        total_revenue = 0.0
        rows = db.query(RevenueSource).all()
        total_revenue = sum(float(r.amount) for r in rows)

        # Count active items
        products_count = db.query(DigitalProduct).count()
        projects_count = db.query(CodingProject).count()
        content_count = db.query(PublishedContent).count()
        trades_open = db.query(TradeEntry).filter_by(status="open").count()
        leads_count = db.query(FreelanceLead).filter_by(status="applied").count()
        deals_count = db.query(BusinessDeal).filter_by(status="lead").count()

        # Strategies summary
        strategies = db.query(EarningStrategy).all()
        executions = db.query(StrategyExecution).order_by(
            StrategyExecution.created_at.desc()
        ).limit(20).all()

        return {
            "wallet": wallet,
            "stop_loss": sl,
            "total_revenue": round(total_revenue, 2),
            "counts": {
                "digital_products": products_count,
                "coding_projects": projects_count,
                "published_content": content_count,
                "open_trades": trades_open,
                "freelance_leads": leads_count,
                "business_deals": deals_count,
            },
            "strategies": [
                {"name": s.name, "enabled": s.enabled, "risk": s.risk_level}
                for s in strategies
            ],
            "recent_executions": [
                {
                    "strategy": e.strategy_name,
                    "action": e.action,
                    "time": e.created_at.isoformat(),
                    "revenue": float(e.revenue_generated),
                }
                for e in executions[:10]
            ],
        }
    finally:
        db.close()