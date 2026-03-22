import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from engine import ExperimentEngine
from lightbar import LightbarDriver
from models import EngineStatus, PromptRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

engine: ExperimentEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    settings = get_settings()
    lb = LightbarDriver(
        device_id=settings.device_id,
        ip=settings.device_ip,
        local_key=settings.device_key,
        version=settings.device_version,
    )
    engine = ExperimentEngine(lb, settings)
    await engine.start()
    logger.info("Engine started")
    yield
    await engine.stop()
    logger.info("Engine stopped")


app = FastAPI(title="Lightbar AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/cam", response_class=HTMLResponse)
def cam():
    return """<!doctype html><html><body style="margin:0;background:#000">
<video id="v" autoplay style="width:100vw;height:100vh;object-fit:cover"></video>
<script>navigator.mediaDevices.getUserMedia({video:true}).then(s=>{document.getElementById('v').srcObject=s})</script>
</body></html>"""


@app.get("/api/status", response_model=EngineStatus)
def get_status():
    if not engine:
        raise HTTPException(503, "Engine not ready")
    return engine.get_status()


@app.get("/api/experiments")
def get_experiments():
    if not engine:
        raise HTTPException(503, "Engine not ready")
    return list(reversed(engine.experiment_history))


@app.get("/api/log")
def get_log(limit: int = 50):
    if not engine:
        raise HTTPException(503, "Engine not ready")
    entries = list(engine.log_entries)[-limit:]
    return entries


@app.post("/api/prompt")
def inject_prompt(body: PromptRequest):
    if not engine:
        raise HTTPException(503, "Engine not ready")
    if not body.prompt.strip():
        raise HTTPException(400, "Prompt cannot be empty")
    engine.inject_prompt(body.prompt.strip())
    return {"ok": True, "message": "Prompt received — will take effect on next program cycle"}


@app.get("/api/stream")
async def stream_events():
    """SSE endpoint — pushes LogEntry JSON objects as they are emitted."""
    if not engine:
        raise HTTPException(503, "Engine not ready")

    q = engine.subscribe_sse()

    async def event_generator():
        try:
            # Replay last 20 log entries so the client has context immediately
            for entry in list(engine.log_entries)[-20:]:
                yield f"data: {entry.model_dump_json()}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            engine.unsubscribe_sse(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Static frontend ───────────────────────────────────────────────────────────

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
else:
    @app.get("/")
    def root():
        return {"message": "Frontend not built. Run: cd frontend && npm run build"}
