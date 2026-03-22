# Core Principles

Last synchronized: 2026-03-22

## Architecture

- **Backend-first**: all device logic lives in the backend. Frontend is display + steering only.
- **Single source of truth**: `engine.py` owns current state. The UI reads it via `/api/status` and `/api/stream` (SSE).
- **Minimal AI calls**: one Haiku call per program cycle (~7 min). No per-step AI calls.
- **Python-side transitions**: color interpolation runs in Python at ~5 Hz. The device gets a new HSV value every 200 ms during transitions.

## Device constraints

- Hue: 0–360 (float), Saturation: 0–100 (float), Value: 0–100 (float) — clamp all inputs.
- DP 24 format: `HHHHSSSSVVVV` — each component scaled to 0–1000, 4 hex digits.
- Mode must be `colour` (DP 21) before colour commands are accepted.
- Power DP 20: `True` = on, `False` = off.
- Socket timeout: 5 seconds. Reconnect on failure; never crash the engine on device errors.

## AI engine rules

- Model: `claude-haiku-4-5-20251001`. Never change without human approval.
- System prompt is short and stable (prompt cache friendly).
- User context per call: time, weather snippet, last 3 themes, optional user prompt.
- Output: JSON with `theme`, `inspiration`, `description`, `duration_minutes` (4–15), `steps` (4–12).
- On parse failure: log error, retry once with explicit JSON instruction, then fall back to a default program.
- User prompt injection: immediately terminates current program, included in next generation.

## Security

- No secrets in source. `.env` only.
- Input from the user prompt field is passed as-is to the AI — the AI is the sanitisation layer (it only outputs color JSON).
- No external write access from the frontend. The `/api/prompt` endpoint is the only mutation.

## Frontend

- Mantine v7, dark theme.
- No state management library — React Query + useState sufficient.
- SSE stream drives the console log. Poll `/api/status` every 5 seconds for status card.
