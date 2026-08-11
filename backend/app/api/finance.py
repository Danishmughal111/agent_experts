"""Finance API - owner-protected. All money actions go through the ledger."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.auth import verify_owner
from app.agents import finance
from app.models import Deal
from app.db import SessionLocal


router = APIRouter()


class DepositIn(BaseModel):
    amount: float
    note: str = ""


class ExpenseIn(BaseModel):
    amount: float
    description: str


class DealIn(BaseModel):
    customer: str
    title: str
    amount: float
    cost: float = 0.0


class DealAction(BaseModel):
    deal_id: int
    received_amount: Optional[float] = None


class WithdrawIn(BaseModel):
    amount: float


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/balance")
def balance(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.get_balance(db)


@router.post("/deposit")
def do_deposit(body: DepositIn, db=Depends(get_db), _=Depends(verify_owner)):
    return finance.deposit(db, body.amount, note=body.note)


@router.post("/expense")
def do_expense(body: ExpenseIn, db=Depends(get_db), _=Depends(verify_owner)):
    return finance.record_expense(db, body.amount, body.description)


@router.post("/deals")
def new_deal(body: DealIn, db=Depends(get_db), _=Depends(verify_owner)):
    d = finance.create_deal(db, body.customer, body.title, body.amount, body.cost)
    return {"id": d.id, "customer": d.customer, "title": d.title,
            "amount": float(d.amount), "status": d.status}


@router.post("/deals/invoice")
def invoice(body: DealAction, db=Depends(get_db), _=Depends(verify_owner)):
    try:
        d = finance.invoice_deal(db, body.deal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": d.id, "status": d.status}


@router.post("/deals/confirm-payment")
def confirm(body: DealAction, db=Depends(get_db), _=Depends(verify_owner)):
    """Owner confirms the customer payment arrived (e.g. on Payoneer). Agent
    computes profit and notifies the owner what they received."""
    try:
        d = finance.confirm_payment(db, body.deal_id, body.received_amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": d.id, "status": d.status, "profit": float(d.profit),
            "customer": d.customer, "title": d.title}


@router.post("/withdraw")
def do_withdraw(body: WithdrawIn, db=Depends(get_db), _=Depends(verify_owner)):
    try:
        return finance.withdraw(db, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ledger")
def ledger(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.ledger_history(db)


@router.get("/notifications")
def notifications(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.list_notifications(db)


@router.post("/notifications/read")
def mark_read(db=Depends(get_db), _=Depends(verify_owner)):
    finance.mark_notifications_read(db)
    return {"ok": True}


@router.get("/tasks")
def tasks(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.task_history(db)


@router.get("/stop-loss")
def stop_loss(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.check_stop_loss(db)


@router.post("/stop-loss/reset")
def stop_loss_reset(db=Depends(get_db), _=Depends(verify_owner)):
    return finance.reset_stop_loss(db)

@router.get("/deals")
def list_deals(db=Depends(get_db), _=Depends(verify_owner)):
    rows = db.query(Deal).order_by(Deal.created_at.desc()).limit(100).all()
    return [{"id": d.id, "customer": d.customer, "title": d.title,
             "amount": float(d.amount), "cost": float(d.cost),
             "profit": float(d.profit or 0), "status": d.status} for d in rows]

