# AGENTS.md — Lightbar AI Control System

## 1. Purpose

This project gives an AI agent autonomous control over an RGB lightbar (Battletron Gaming Light Bar, Tuya v3.5) to create ever-changing, contextually inspired light programs. The human provides a UI to observe, steer, and override the AI's work.

`docs/memory/` is the operational memory agents must use. Read it before doing any implementation work.

## 2. Required Startup Routine

Before any implementation work:

1. Read `docs/memory/INDEX.md` — orientation and current state.
2. Read `docs/memory/core-principles.md` — architecture rules and constraints.
3. Read `docs/memory/workflow.md` — how to make changes.
4. Read `docs/memory/records/decision-log.md` — why things are the way they are.
5. Read `docs/memory/records/experiment-log.md` — what the light engine has learned.

## 3. Memory Model

- **Orientation**: `docs/memory/INDEX.md`
- **Stable**: `docs/memory/core-principles.md` — architecture, constraints, device facts
- **Process**: `docs/memory/workflow.md` — how to develop, test, deploy
- **Evidence**: `docs/memory/records/` — decisions, experiments, DP discoveries

## 4. Project Guardrails

Agents must preserve these while coding:

- **Device safety**: never send out-of-range values (hue 0–360, sat/val 0–100). Clamp all inputs.
- **Token budget**: AI generation uses `claude-haiku-4-5-20251001`. Do not switch to a heavier model for the engine loop without explicit human approval.
- **LAN-only**: the backend communicates directly with the device IP (set in `.env`) over TCP 6668. No cloud relay.
- **No secrets in source**: credentials live in `.env` only, which is gitignored.
- **No Docker for now**: runs bare on Mac. VPS migration is a future concern.
- **Stateless AI calls**: each program generation is a single, context-minimal API call. No conversation history in the engine loop.

## 5. AI Engine Rules

The AI engine is the creative core of the system. When extending it:

- Programs are JSON: a theme, description, and array of `ColorStep` objects.
- The engine executes steps sequentially, looping for `duration_minutes`.
- A pending user prompt immediately terminates the current program and seeds the next generation.
- The engine must log all significant events to `console_log` so the UI can display them.
- Claude Haiku generates the program — one call per cycle. Keep system prompt short (cached).
- Inspiration sources: time of day, Open-Meteo weather (free, no key), cycle memory (last 3 themes).

## 6. Definition of Done

A task is not done until:

1. Code runs without errors.
2. The lightbar responds correctly.
3. `docs/memory/records/decision-log.md` is updated with any non-obvious choices.
4. The UI reflects the new capability.
