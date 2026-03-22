# Architecture

## Overview

```
┌─────────────────────────────────────────────────────┐
│  Browser (Mac)                                       │
│  React + Mantine UI                                  │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Status Panel │ │ Console  │ │  Prompt Input    │ │
│  └──────┬───────┘ └────┬─────┘ └────────┬─────────┘ │
│         │ poll /status  │ SSE /stream    │ POST /prompt
└─────────┼───────────────┼───────────────┼────────────┘
          │               │               │
┌─────────▼───────────────▼───────────────▼────────────┐
│  FastAPI Backend (port 8000)                          │
│  ┌────────────────────────────────────────────────┐  │
│  │ ExperimentEngine (asyncio background task)     │  │
│  │  ┌────────────────┐   ┌──────────────────────┐ │  │
│  │  │ AI Generator   │   │ Step Executor        │ │  │
│  │  │ (Haiku call)   │   │ (HSV interpolation   │ │  │
│  │  │ ~1 call/7 min  │   │  @ 5 Hz)             │ │  │
│  │  └───────┬────────┘   └──────────┬───────────┘ │  │
│  └──────────┼────────────────────────┼─────────────┘  │
│             │                        │               │
│  ┌──────────▼────────┐    ┌──────────▼────────────┐ │
│  │ Anthropic API     │    │ LightbarDriver        │ │
│  │ claude-haiku      │    │ (tinytuya BulbDevice) │ │
│  └───────────────────┘    └───────────────────────┘ │
└──────────────────────────────────────────────────────┘
                                  │ TCP 6668
                     ┌────────────▼────────────┐
                     │ Battletron Light Bar    │
                     │ <DEVICE_IP>             │
                     │ Tuya v3.5               │
                     └─────────────────────────┘
```

## Engine lifecycle

1. Backend starts → engine starts → generates first program (Haiku call).
2. Engine executes program: loops through color steps with HSV interpolation.
3. When program duration expires → generate next program.
4. If user posts to `/api/prompt` → pending_prompt is set → current program aborts → next generation includes the prompt.
5. All log events are pushed to an in-memory queue consumed by SSE clients.

## API surface

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Current device state + active experiment |
| GET | `/api/experiments` | Last 20 completed experiments |
| POST | `/api/prompt` | Inject user steering prompt |
| GET | `/api/stream` | SSE — real-time console events |
| GET | `/api/health` | Health check |

## Data flow: color step

```
Haiku JSON step → ColorStep(hue, sat, val, duration_ms, transition_ms)
    → _execute_step():
        for each 200ms tick during transition_ms:
            interpolated HSV = lerp(prev, target, t)
            tinytuya.set_value(24, hsv_to_tuya_hex(h, s, v))   [in executor]
        hold at target color for remaining duration_ms
```
