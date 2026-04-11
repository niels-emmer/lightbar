# docs/memory/INDEX.md — Lightbar Session Orientation

Last updated: 2026-04-11

## What this project is

An AI-controlled RGB lightbar. A FastAPI backend drives a Battletron Gaming Light Bar (Tuya v3.5) on the local LAN. A Claude Haiku loop generates "light programs" (JSON color sequences) autonomously, cycling every ~7 minutes. A React/Mantine UI lets the human observe and steer. All 20 LED segments are individually addressable via DP 61.

## Current status

- [x] Project scaffolded
- [x] Backend: FastAPI + tinytuya driver + AI engine
- [x] Frontend: React + Mantine console/status/prompt UI + power/skip controls
- [x] First live run with real device
- [x] DP 61 per-segment colour control mapped (2026-04-11) — 20 segments, 1-based index
- [x] 7 spatial segment patterns added (gradient, plasma, comet, ripple, twinkle, ember, split)
- [x] 2 new whole-bar patterns added (palette_cycle, glitch)
- [x] Power on/off and skip API + UI controls
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
- Color DP 24: 12-char hex `HHHHSSSSVVVV`, each 0–1000 as 4-digit hex (whole bar, requires DP 21 = `'colour'`)
- Segment DP 61: base64 13-byte payload, controls one of 20 segments; DP 21 must be **`'colour'`** (device silently drops DP 61 in `'scene'` mode)
- Hardware scene DP 51: native device animations (flow, flash, wave), set once and device runs them
- AI model: `claude-haiku-4-5-20251001` — haiku only, stateless, max 800 tokens out
- Whole-bar patterns update at 10 Hz; segment patterns sweep all 20 LEDs every ~4s (0.20s/segment minimum safe delay)
- Backend port: 8000 (container), 8042 (host-mapped). Frontend dev port: 5173
- Secrets: `.env` (gitignored)

## Pattern inventory

### Whole-bar (single HSV at 10 Hz)
`breathe`, `wheel`, `pulse`, `strobe`, `aurora`, `lfo_pair`, `thunder`, `campfire`, `drift`, `palette_cycle`, `glitch`

### Segment (20 individual LEDs, ~4s per sweep)
`gradient`, `plasma`, `comet`, `ripple`, `twinkle`, `ember`, `split`

### Hardware scene (native device, set-and-forget)
`scene` — scene_type 0=static, 1=flow, 2=flash, 3=wave
