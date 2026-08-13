"""Finance engine: wallet ledger, deals, profit calculation, stop-loss.
This is where the REAL money math happens - no fake simulation.
The agent only operates on its ALLOCATED balance (real lesson: it sees its own
budget, not your full Payoneer/bank balance)."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models import (AgentTask, Deal, LedgerEntry, Notification, StopLossState,
                        Wallet)
from app.config import get_settings


def _dec(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _wallet(db: Session) -> Wallet:
    w = db.query(Wallet).first()
    if not w:
        w = Wallet(allocated_balance=_dec(get_settings().initial_balance),
                   currency=get_settings().base_currency,
                   real_money_note="Stored externally (Payoneer/bank)")
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def get_balance(db: Session) -> dict:
    w = _wallet(db)
    return {
        "allocated_balance": float(w.allocated_balance),
        "currency": w.currency,
        "real_money_note": w.real_money_note,
    }


def _set_balance(db: Session, w: Wallet, new_balance: Decimal):
    w.allocated_balance = _dec(new_balance)
    db.commit()


def _ledger(db: Session, direction, category, amount, desc, deal_id=None):
    w = _wallet(db)
    bal_before = _dec(w.allocated_balance)
    if direction == "credit":
        new_bal = bal_before + _dec(amount)
    else:
        new_bal = bal_before - _dec(amount)
    _set_balance(db, w, new_bal)
    entry = LedgerEntry(direction=direction, category=category, amount=_dec(amount),
                        balance_after=_dec(new_bal), currency=w.currency,
                        description=desc, deal_id=deal_id)
    db.add(entry)
    db.commit()
    return entry


def deposit(db: Session, amount, currency="", note=""):
    amount = _dec(amount)
    _ledger(db, "credit", "deposit", amount, f"Deposit to agent wallet. {note}".strip())
    notify(db, "Deposit", f"Deposited {amount} into agent wallet.")
    return get_balance(db)


def record_expense(db: Session, amount, desc):
    amount = _dec(amount)
    _ledger(db, "debit", "expense", amount, desc)
    return get_balance(db)


def create_deal(db: Session, customer, title, amount, cost=0):
    amount = _dec(amount)
    deal = Deal(customer=customer, title=title, amount=amount,
                cost=_dec(cost), status="proposed")
    db.add(deal)
    db.commit()
    db.refresh(deal)
    _add_task(db, "deal_created",
              f"Deal created for {customer}: {title} ({amount})")
    return deal


def invoice_deal(db: Session, deal_id):
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise ValueError("Deal not found")
    deal.status = "invoiced"
    db.commit()
    _add_task(db, "deal_invoiced", f"Invoice sent for deal {deal.id}")
    return deal


def confirm_payment(db: Session, deal_id, received_amount=None):
    """Owner confirms real payment arrived (e.g. via Payoneer).
    The agent computes profit and notifies the owner what they received."""
    deal = db.query(Deal).get(deal_id)
    if not deal:
        raise ValueError("Deal not found")
    received = _dec(received_amount if received_amount is not None else deal.amount)
    profit = received - deal.cost
    deal.amount = deal.amount  # keep invoice amount
    deal.profit = _dec(profit)
    deal.status = "settled"
    # Record credit of the profit into the wallet
    _ledger(db, "credit", "profit", _dec(profit),
            f"Profit from deal {deal.id} ({deal.customer}) - {deal.title}", deal_id=deal.id)
    db.commit()
    notify(db, "Payment received", f"Customer paid {received} for {deal.title}. "
                                   f"After cost {deal.cost}, your profit is {profit}.",
           level="success")
    _add_task(db, "payment_confirmed", f"Deal {deal.id} settled. Profit {profit}")
    return deal


def withdraw(db: Session, amount):
    amount = _dec(amount)
    w = _wallet(db)
    if amount > w.allocated_balance:
        raise ValueError("Insufficient allocated balance to withdraw")
    _ledger(db, "debit", "withdrawal", amount, "Profit/balance withdrawn by owner")
    notify(db, "Withdrawal", f"Withdrew {amount} from agent wallet.")
    return get_balance(db)


# ---------------- Stop-loss ----------------
def check_stop_loss(db: Session) -> dict:
    w = _wallet(db)
    settings = get_settings()
    st = db.query(StopLossState).first()
    if not st:
        st = StopLossState(daily_start_balance=_dec(w.allocated_balance), halted=False)
        db.add(st)
        db.commit()
        db.refresh(st)

    bal = _dec(w.allocated_balance)
    total_loss_pct = 0.0
    if getattr(settings, "initial_balance", 0):
        initial = _dec(settings.initial_balance)
        if initial:
            total_loss_pct = float((bal - initial) / initial * 100)

    reasons = []
    # $0-start fix: only halt when the balance drops below a POSITIVE floor
    # (a real loss scenario), never when the machine simply starts at zero.
    floor = _dec(settings.min_balance_threshold)
    if floor > 0 and bal <= floor:
        reasons.append(f"Balance {bal} below minimum threshold {floor}")
    elif bal < 0:
        reasons.append(f"Balance is negative ({bal}) — more spent than allocated")
    if total_loss_pct <= -settings.total_loss_limit_pct:
        reasons.append(f"Total loss {total_loss_pct:.1f}% exceeds limit {-settings.total_loss_limit_pct}%")

    if reasons:
        st.halted = True
        st.halt_reason = "; ".join(reasons)
        notify(db, "STOP-LOSS TRIGGERED", "; ".join(reasons), level="danger")
        db.commit()
        _add_task(db, "stop_loss_halted", "; ".join(reasons))
    return {"halted": st.halted, "reason": st.halt_reason, "balance": float(bal)}


def reset_stop_loss(db: Session):
    st = db.query(StopLossState).first()
    w = _wallet(db)
    if not st:
        st = StopLossState()
        db.add(st)
    st.halted = False
    st.halt_reason = ""
    st.daily_start_balance = _dec(w.allocated_balance)
    db.commit()
    return {"halted": False}


def ledger_history(db: Session, limit=100):
    rows = db.query(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "direction": r.direction, "category": r.category,
             "amount": float(r.amount), "balance_after": float(r.balance_after),
             "description": r.description, "time": r.created_at} for r in rows]


# ---------------- Notifications ----------------
def notify(db: Session, title, body, level="info"):
    n = Notification(title=title, body=body, level=level)
    db.add(n)
    db.commit()


def list_notifications(db: Session, unread_only=False):
    q = db.query(Notification).order_by(Notification.created_at.desc())
    if unread_only:
        q = q.filter(Notification.read.is_(False))
    rows = q.limit(50).all()
    return [{"id": r.id, "title": r.title, "body": r.body, "level": r.level,
             "read": r.read, "time": r.created_at} for r in rows]


def mark_notifications_read(db: Session):
    for r in db.query(Notification).filter(Notification.read.is_(False)).all():
        r.read = True
    db.commit()


def _add_task(db: Session, action, detail, result=""):
    t = AgentTask(action=action, detail=detail, result=result)
    db.add(t)
    db.commit()


def task_history(db: Session, limit=100):
    rows = db.query(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "action": r.action, "detail": r.detail,
             "result": r.result, "time": r.created_at} for r in rows]
