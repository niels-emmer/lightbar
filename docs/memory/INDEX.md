# docs/memory/INDEX.md — Lightbar Session Orientation

Last updated: 2026-03-22

## What this project is

An AI-controlled RGB lightbar. A FastAPI backend drives a Battletron Gaming Light Bar (Tuya v3.5) on the local LAN. A Claude Haiku loop generates "light programs" (JSON color sequences) autonomously, cycling every ~7 minutes. A React/Mantine UI lets the human observe and steer.

## Current status

- [x] Project scaffolded
- [x] Backend: FastAPI + tinytuya driver + AI engine skeleton
- [x] Frontend: React + Mantine console/status/prompt UI
- [ ] First live run with real device
- [ ] DP 46/47/53 mapping (scene/effect params — unknown)

## Memory files to read

| File | When to read |
|------|-------------|
| `core-principles.md` | Before any code change |
| `workflow.md` | Before implementing a feature |
| `records/decision-log.md` | Before making architectural choices |
| `records/experiment-log.md` | Before changing the AI engine |
| `records/dp-map.md` | Before changing device control code |

## Key facts

- Device: Battletron Gaming Light Bar, Tuya v3.5, port TCP 6668 (IP in `.env`)
- Color DP 24: 12-char hex `HHHHSSSSVVVV`, each 0–1000 as 4-digit hex
- AI model: `claude-haiku-4-5-20251001` — haiku only, stateless, max 400 tokens out
- Backend port: 8000, Frontend dev port: 5173
- Secrets: `.env` (gitignored)
