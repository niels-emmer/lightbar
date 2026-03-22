# CLAUDE.md — Lightbar

Always read `docs/memory/INDEX.md` at the start of each session.

## Stack

- **Backend**: Python 3.12, FastAPI, tinytuya, anthropic SDK
- **Frontend**: React 18, Vite, TypeScript, Mantine UI v7
- **AI Engine**: claude-haiku-4-5-20251001 (low cost, stateless calls)
- **Device**: Battletron Gaming Light Bar, Tuya v3.5 (IP in `.env`)

## Run

```bash
# Backend
cd backend && pip install -r requirements.txt
cp ../.env.example ../.env  # then fill in ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev   # dev: http://localhost:5173
npm run build                               # prod: dist/ served by backend
```

## Key files

- `backend/engine.py` — AI experiment loop
- `backend/lightbar.py` — tinytuya device wrapper
- `backend/main.py` — FastAPI routes + SSE stream
- `frontend/src/components/Console.tsx` — live AI log
- `frontend/src/components/PromptInput.tsx` — user steering

## Device credentials

In `.env` — never commit. See `docs/device-protocol.md` for DP reference.
