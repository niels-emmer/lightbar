# Decision Log

## 2026-03-22 — Initial architecture

**Decision**: Use `claude-haiku-4-5-20251001` for the engine loop, not sonnet.
**Reason**: Human explicitly asked for low token consumption. Haiku is ~10x cheaper and sufficient for generating color JSON with a light creative brief.

**Decision**: Programs are JSON color sequences executed by Python, not by the AI step-by-step.
**Reason**: Continuous AI calls would be extremely expensive and slow. One call per 7-minute cycle keeps daily cost at roughly $0.01–0.05.

**Decision**: Color transitions implemented as Python-side HSV interpolation at ~5 Hz.
**Reason**: The device does not expose a reliable transition API (DPs 46/47/53 are unmapped). Python-side gives full control and is deterministic.

**Decision**: SSE (`/api/stream`) for real-time UI updates.
**Reason**: Consistent with other projects (wall-cast). Simpler than WebSocket for a one-directional feed.

**Decision**: No Docker for initial deployment.
**Reason**: Runs on Mac on same LAN as device. Docker adds complexity with no benefit yet. Migration path to VPS documented in `workflow.md`.

**Decision**: Open-Meteo as the weather inspiration source.
**Reason**: Free, no API key, no rate limit concerns for a single-client use case. Returns weather code + temperature — enough for mood context.

**Decision**: Backend serves the built frontend static files.
**Reason**: Single process, no nginx needed for local Mac run. In prod (VPS), nginx proxy is the path forward.
