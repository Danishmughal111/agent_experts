# Agent Experts - Personal AI Business Agent

Your personal AI business agent that helps you earn money legally, track every
transaction in a real ledger (no fake simulation), notify you when customers
pay, and protect you with automatic stop-loss rules.

## How it works

- Agent has its own ALLOCATED wallet balance in the database. It only ever
  operates within that budget (it does NOT see your full Payoneer/bank balance).
- Real money is held externally (Payoneer, bank). You record deposits and
  withdrawals; the agent tracks and reports everything.
- Agent creates customer deals, sends invoices, and NOTIFIES you when a
  customer payment arrives so you can confirm it on Payoneer.
- After you confirm, the agent automatically computes your profit
  (received - cost) and updates the wallet.
- Stop-loss protection: if the allocated balance falls below a threshold or
  total losses exceed a limit, the agent halts and waits for your review.

## Tech stack
- Backend: Python FastAPI + SQLAlchemy + DeepSeek (OpenAI-compatible)
- Database: Supabase (Postgres) or local SQLite
- Frontend: Next.js (React/TypeScript), chatbot-style + dashboard

## APIs
- `/health` - health check
- `POST /login` - owner login `{password}`
- `POST /chat` - ask agent (header `X-Agent-Token`)
- `GET /api/balance` - agent wallet balance
- `POST /api/deposit` - add money `{amount}`
- `POST /api/expense` - record spend `{amount, description}`
- `POST /api/deals` - create customer deal
- `POST /api/deals/invoice` - send invoice
- `POST /api/deals/confirm-payment` - confirm customer paid
- `POST /api/withdraw` - withdraw profit/balance
- `GET /api/ledger` - full transaction history
- `GET /api/notifications` - alerts (e.g. payment received, stop-loss)
- `GET /api/tasks` - what the agent did
- `GET /api/stop-loss` / `POST /api/stop-loss/reset`

## Deploy to Render (2 Web Services)

Render Blueprint is NOT free, so create two free Web Services:

### 1) Backend Web Service
- New + -> Web Service -> your repo
- Root Directory: (leave empty / repo root)
- Build: uses the root `Dockerfile`
- Environment variables:
  ```
  DATABASE_URL = <Supabase Postgres conn string>
  OPENAI_API_KEY = <DeepSeek key>
  OPENAI_MODEL = deepseek-chat
  OPENAI_BASE_URL = https://api.deepseek.com
  SECRET_KEY = <long random string>
  OWNER_PASSWORD = <your owner password>
  AGENT_TOKEN = <your agent token>
  APP_ENV = production
  BASE_CURRENCY = USD   (or PKR)
  INITIAL_BALANCE = 1000
  DAILY_LOSS_LIMIT_PCT = 10
  TOTAL_LOSS_LIMIT_PCT = 20
  MAX_TRADE_SIZE_PCT = 10
  MIN_BALANCE_THRESHOLD = 200
  ```
- Health Check Path: `/health`
- Note URL: https://{your-backend}.onrender.com

### 2) Frontend Web Service
- New + -> Web Service -> your repo
- Root Directory: `frontend`
- Build: uses `frontend/Dockerfile`
- Environment variable:
  ```
  NEXT_PUBLIC_API_URL = https://{your-backend}.onrender.com
  ```
- Note: on Render set `DATABASE_URL` etc. on the backend service only.

### Local run (backend)
```bash
cd backend
pip install -r requirements.txt
setx  # or export
DATABASE_URL=sqlite:///./dev.db OPENAI_MODEL=deepseek-chat \
OPENAI_BASE_URL=https://api.deepseek.com SECRET_KEY=dev OWNER_PASSWORD=admin \
AGENT_TOKEN=agent-secret python -m uvicorn app.main:app --reload
```
Then open http://localhost:8000/docs

### Payoneer auto-detection (future)
The finance engine is built so a Payoneer API provider can be plugged in later
to automatically detect incoming payments instead of manual confirmation.
