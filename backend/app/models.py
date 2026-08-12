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


# ============================================================
# AI EARNING MACHINE — Strategy Models
# ============================================================

class EarningStrategy(Base):
    """Active AI earning strategies with config."""
    __tablename__ = "earning_strategy"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)  # freelance, content, trading, coding, digital_products, business, api_monetize
    display_name = Column(String(255))
    enabled = Column(Boolean, default=True)
    risk_level = Column(String(20), default="medium")  # low, medium, high
    daily_profit_target = Column(Numeric(20, 4), default=Decimal("0.0000"))
    daily_loss_limit = Column(Numeric(20, 4), default=Decimal("0.0000"))
    max_concurrent = Column(Integer, default=5)
    config_json = Column(Text, default="{}")  # strategy-specific config as JSON
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class StrategyExecution(Base):
    """Each time a strategy runs, log here."""
    __tablename__ = "strategy_execution"
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("earning_strategy.id"), nullable=True)
    strategy_name = Column(String(100))
    action = Column(String(100))  # started, completed, failed, proposed
    detail = Column(Text, default="")
    result = Column(Text, default="")
    profit = Column(Numeric(20, 4), default=Decimal("0.0000"))
    cost = Column(Numeric(20, 4), default=Decimal("0.0000"))
    revenue_generated = Column(Numeric(20, 4), default=Decimal("0.0000"))
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)


class RevenueSource(Base):
    """Tracking all income streams."""
    __tablename__ = "revenue_source"
    id = Column(Integer, primary_key=True)
    source_type = Column(String(50))  # freelance, content_ad, content_affiliate, digital_product, trading, coding, business, api
    description = Column(Text, default="")
    amount = Column(Numeric(20, 4))
    currency = Column(String(8), default="USD")
    platform = Column(String(100))  # gumroad, upwork, stripe, alpaca, binance, etc.
    external_ref = Column(String(255))  # external platform reference/ID
    settled = Column(Boolean, default=False)  # confirmed payment
    payoneer_txn_id = Column(String(255), default="")
    created_at = Column(DateTime, default=utcnow)


# --- MODULE 2: Freelance ---
class FreelanceLead(Base):
    """Freelance gigs found and tracked."""
    __tablename__ = "freelance_lead"
    id = Column(Integer, primary_key=True)
    platform = Column(String(50))  # upwork, fiverr, peopleperhour
    gig_id = Column(String(100))
    title = Column(String(500))
    description = Column(Text)
    budget = Column(Numeric(20, 4), default=Decimal("0.0000"))
    currency = Column(String(8), default="USD")
    proposal_sent = Column(Boolean, default=False)
    proposal_text = Column(Text)
    status = Column(String(30), default="new")  # new, applied, accepted, completed, rejected
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)


# --- MODULE 3: Content ---
class PublishedContent(Base):
    """Content published for monetization."""
    __tablename__ = "published_content"
    id = Column(Integer, primary_key=True)
    platform = Column(String(50))  # wordpress, medium, blogger, twitter, linkedin
    title = Column(String(500))
    url = Column(String(1000))
    content_type = Column(String(30))  # blog, social_post, video_description, newsletter
    affiliate_links = Column(Text)  # JSON list of affiliate URLs
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    revenue = Column(Numeric(20, 4), default=Decimal("0.0000"))
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    published_at = Column(DateTime, default=utcnow)


# --- MODULE 4: Digital Products ---
class DigitalProduct(Base):
    """Digital products listed on Gumroad etc."""
    __tablename__ = "digital_product"
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    description = Column(Text)
    product_type = Column(String(50))  # ebook, template, course, code, design, canva
    platform = Column(String(50))  # gumroad, etsy, shopify
    external_id = Column(String(255))  # gumroad product ID etc.
    external_url = Column(String(1000))
    price = Column(Numeric(20, 4), default=Decimal("0.0000"))
    currency = Column(String(8), default="USD")
    sales_count = Column(Integer, default=0)
    total_revenue = Column(Numeric(20, 4), default=Decimal("0.0000"))
    status = Column(String(30), default="draft")  # draft, listed, active, paused
    file_path = Column(String(1000))  # local file path
    created_at = Column(DateTime, default=utcnow)


# --- MODULE 5: Trading ---
class TradeEntry(Base):
    """Stock/Crypto trade records."""
    __tablename__ = "trade_entry"
    id = Column(Integer, primary_key=True)
    platform = Column(String(50))  # alpaca, binance
    symbol = Column(String(20))  # AAPL, BTCUSDT, etc.
    trade_type = Column(String(10))  # buy, sell
    quantity = Column(Numeric(20, 8))
    entry_price = Column(Numeric(20, 4))
    exit_price = Column(Numeric(20, 4), default=Decimal("0.0000"))
    profit_loss = Column(Numeric(20, 4), default=Decimal("0.0000"))
    status = Column(String(20), default="open")  # open, closed, cancelled
    risk_score = Column(Float, default=0.0)  # AI risk assessment 0-100
    ai_reasoning = Column(Text)
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    opened_at = Column(DateTime, default=utcnow)
    closed_at = Column(DateTime, nullable=True)


# --- MODULE 6: Coding Agent ---
class CodingProject(Base):
    """Coding tasks/projects the agent works on."""
    __tablename__ = "coding_project"
    id = Column(Integer, primary_key=True)
    platform = Column(String(50))  # fiverr, upwork, internal
    project_type = Column(String(50))  # website, api, script, extension, automation, template
    title = Column(String(500))
    requirements = Column(Text)
    language = Column(String(50))  # python, javascript, typescript, html, etc.
    status = Column(String(30), default="analyzing")  # analyzing, coding, testing, delivered, paid
    github_repo = Column(String(500))
    delivery_url = Column(String(1000))
    deliverables = Column(Text)  # JSON: list of files
    client_name = Column(String(255))
    budget = Column(Numeric(20, 4), default=Decimal("0.0000"))
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)


# --- MODULE 7: Business Website & Agent ---
class BusinessDeal(Base):
    """Business sales pipeline (from agent's own website)."""
    __tablename__ = "business_deal"
    id = Column(Integer, primary_key=True)
    lead_name = Column(String(255))
    lead_email = Column(String(255))
    service_type = Column(String(100))  # coding, content, design, consulting
    requirements = Column(Text)
    status = Column(String(30), default="lead")  # lead, contacted, negotiating, won, lost
    deal_value = Column(Numeric(20, 4), default=Decimal("0.0000"))
    notes = Column(Text)
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    closed_at = Column(DateTime, nullable=True)


class WebsiteInstance(Base):
    """Websites built by the agent for its own business."""
    __tablename__ = "website_instance"
    id = Column(Integer, primary_key=True)
    domain = Column(String(500))
    platform = Column(String(50))  # vercel, netlify, custom
    deploy_url = Column(String(1000))
    site_type = Column(String(50))  # portfolio, agency, store, blog
    status = Column(String(30), default="active")
    total_revenue = Column(Numeric(20, 4), default=Decimal("0.0000"))
    created_at = Column(DateTime, default=utcnow)


# --- Payoneer Tracking ---
class PayoneerTransaction(Base):
    """Track real Payoneer incoming payments."""
    __tablename__ = "payoneer_transaction"
    id = Column(Integer, primary_key=True)
    external_ref = Column(String(255))  # Payoneer transaction ID
    amount = Column(Numeric(20, 4))
    currency = Column(String(8), default="USD")
    payer_name = Column(String(255))
    source_type = Column(String(50))  # gumroad, client, trading, etc.
    status = Column(String(30), default="pending")  # pending, confirmed, failed
    raw_data = Column(Text)  # full webhook JSON
    revenue_source_id = Column(Integer, ForeignKey("revenue_source.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
