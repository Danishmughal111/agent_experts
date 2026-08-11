"""Database models. Uses Supabase/Postgres via SQLAlchemy."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text, Numeric)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class Wallet(Base):
    """Agent's allocated balance. This is the money the agent operates on.
    The real money (Payoneer/bank) lives outside; this is the ledger record
    that drives limits and reporting."""
    __tablename__ = "wallet"
    id = Column(Integer, primary_key=True)
    currency = Column(String(8), default="USD")
    allocated_balance = Column(Numeric(20, 4), default=Decimal("0.0000"))
    real_money_note = Column(Text, default="")  # human note e.g. "stored in Payoneer"
    created_at = Column(DateTime, default=utcnow)


class LedgerEntry(Base):
    """Every real money movement, in and out."""
    __tablename__ = "ledger"
    id = Column(Integer, primary_key=True)
    direction = Column(String(10))  # credit (in) / debit (out)
    category = Column(String(50))   # deposit, expense, profit, loss, fee, withdrawal, transfer
    amount = Column(Numeric(20, 4))
    balance_after = Column(Numeric(20, 4))
    currency = Column(String(8), default="USD")
    description = Column(Text, default="")
    deal_id = Column(Integer, ForeignKey("deal.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Deal(Base):
    """A customer deal/invoice created by the agent."""
    __tablename__ = "deal"
    id = Column(Integer, primary_key=True)
    customer = Column(String(255))
    title = Column(String(255))
    amount = Column(Numeric(20, 4))          # invoice amount
    currency = Column(String(8), default="USD")
    status = Column(String(30), default="proposed")  # proposed -> invoiced -> paid -> settled
    profit = Column(Numeric(20, 4), default=Decimal("0.0000"))  # computed after payment
    cost = Column(Numeric(20, 4), default=Decimal("0.0000"))
    created_at = Column(DateTime, default=utcnow)
    ledger_entries = relationship("LedgerEntry", backref="deal")


class Notification(Base):
    """Notifications for the owner (e.g. 'customer paid $500, check Payoneer')."""
    __tablename__ = "notification"
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    body = Column(Text)
    level = Column(String(20), default="info")  # info, success, warning, danger
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)


class AgentTask(Base):
    """What the agent performed (history)."""
    __tablename__ = "agent_task"
    id = Column(Integer, primary_key=True)
    action = Column(String(100))
    detail = Column(Text, default="")
    result = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class StopLossState(Base):
    """Runtime stop-loss tracking."""
    __tablename__ = "stop_loss"
    id = Column(Integer, primary_key=True)
    halted = Column(Boolean, default=False)
    halt_reason = Column(Text, default="")
    daily_start_balance = Column(Numeric(20, 4), default=Decimal("0.0000"))
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
