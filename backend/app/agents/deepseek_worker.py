"""The AI business agent worker. Uses DeepSeek to reason, and the finance
engine to act on money (always through the ledger + approval)."""
from sqlalchemy.orm import Session

from app import llm
from app.agents import finance
from app.models import AgentTask


SYSTEM = (
    "You are a safety-conscious, profit-seeking business agent. "
    "You only ever operate on your allocated wallet balance. You never touch "
    "any real external account directly. When you make a deal or spend money, "
    "clearly tell the owner what was earned/cost and notify them when a customer "
    "payment arrives so they can confirm it. Be honest and concise."
)


def ask(db: Session, prompt: str) -> str:
    reply = llm.chat(prompt, system=SYSTEM)
    finance._add_task(db, "chat", prompt[:200], reply[:300])
    return reply


def run_cycle(db: Session):
    """A single autonomous step the agent takes."""
    # 1. If stop-loss triggered, do nothing.
    sl = finance.check_stop_loss(db)
    if sl["halted"]:
        return {"status": "halted", "reason": sl["reason"]}

    # 2. Look at balance, propose next best action.
    wallet = finance.get_balance(db)
    prompt = (
        f"My allocated wallet balance is {wallet['allocated_balance']} "
        f"{wallet['currency']}. Propose the single best safe next action "
        "(a paid customer deal, or a small legal spend to win revenue). "
        "Return a short actionable suggestion."
    )
    suggestion = llm.chat(prompt, system=SYSTEM)

    # 3. Record what the agent intends to do (owner must approve money actions).
    finance._add_task(db, "propose", "", suggestion)
    return {"status": "proposed", "suggestion": suggestion, "wallet": wallet,
            "stop_loss": sl}
