"""DeepSeek (OpenAI-compatible) integration. Falls back to deterministic mode
when no API key is set, so the system still works offline/testing."""
from openai import OpenAI
from app.config import get_settings


def get_client():
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def chat(prompt: str, system: str = "You are a smart, safety-conscious business agent.") -> str:
    client = get_client()
    if client is None:
        return deterministic_reply(prompt)
    settings = get_settings()
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:  # fail safe -> deterministic
        return f"[AI offline - {e}] " + deterministic_reply(prompt)


def deterministic_reply(prompt: str) -> str:
    """No-key fallback so the agent is always usable."""
    p = prompt.lower()
    if "balance" in p or "wallet" in p:
        return "Your agent wallet balance is tracked in the ledger. Run /status to see it."
    if "deal" in p or "invoice" in p:
        return "I can create a customer deal and notify you when payment is received."
    if "profit" in p or "earn" in p:
        return "I recommend a safe, reimbursed service model. Start a deal to begin."
    return "I'm your business agent. I can track money, make deals, and notify you on payments. Ask me about balance, deals, or profit."
