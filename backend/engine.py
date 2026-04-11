"""
ExperimentEngine — AI brain + pattern executor.

Architecture:
  - Claude Haiku generates an "experiment": theme + list of acts.
  - Each act specifies a pattern (breathe, wheel, aurora, thunder, …) and its params.
  - Acts play sequentially, cycling until the experiment duration expires.
  - Pattern values are computed in Python at 10 Hz and sent to the device.
  - One Haiku call per experiment cycle (~7 min) keeps token cost minimal.
"""

import asyncio
import json
import logging
import re
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import anthropic

import patterns as pat
from config import Settings
from lightbar import LightbarDriver, tuya_to_hsv
from patterns import SEGMENT_PATTERNS
from models import Experiment, EngineStatus, LogEntry

logger = logging.getLogger(__name__)

TICK = 0.10  # 10 Hz

SYSTEM_PROMPT = (
    "You are a light artist with full creative control over an RGB gaming lightbar. "
    "Create evocative, ever-changing light programs using the pattern vocabulary. "
    "Respond ONLY with valid JSON — no prose, no markdown, no newlines inside strings."
)

PATTERN_CATALOG = """
PATTERNS (pick by name, combine into acts):

━━ Whole-bar patterns — one color, animated by Python ━━
breathe        hue(0-360), saturation(0-100), value_min(0-50), value_max(50-100), period_sec(2-10)
wheel          saturation(0-100), value(20-100), start_hue(0-360), deg_per_sec(10-120)
pulse          hue(0-360), saturation(0-100), value_peak(60-100), period_sec(0.5-4)
strobe         hue(0-360), saturation(0-100), value(60-100), rate_hz(1-10), duty(0.1-0.9)
aurora         center_hue(0-360), hue_range(10-90), saturation(60-100), value_center(30-70), value_range(10-40)
lfo_pair       hue_a(0-360), hue_b(0-360), saturation(0-100), value(20-90), period_sec(4-20)
thunder        bg_hue(200-260), bg_saturation(40-80), bg_value(3-15), flash_rate_per_min(5-25)
campfire       intensity(0.3-1.0)
drift          hue(0-360), saturation(50-100), value(30-70), hue_drift(10-60), value_drift(10-35), speed(0.2-1.0)
palette_cycle  hues([h1,h2,...] 2-6 values 0-360), saturation(0-100), value(30-90), dwell_sec(3-12)
               Dwells on each hue then cross-fades to the next. Great for mood progressions.
               Example: {"pattern":"palette_cycle","hues":[15,45,200,280],"saturation":85,"value":65,"dwell_sec":8,"duration_sec":120}
glitch         base_hue(0-360), saturation(0-100), value(40-80), glitch_rate(0.5-4), glitch_duration(0.05-0.25)
               Steady color spiking with brief random hue flashes. Digital artifact energy.

━━ Segment patterns — each of the 20 LEDs individually addressed ━━
               These update every ~4 seconds (hardware constraint). Design for slow, ambient motion.
gradient       hue_left(0-360), hue_right(0-360), saturation(0-100), value(20-100), speed(0-30)
               Smooth hue spread across bar. speed slowly scrolls it. 0=static, 20=drifting.
               Example: {"pattern":"gradient","hue_left":200,"hue_right":320,"saturation":90,"value":70,"speed":8,"duration_sec":120}
plasma         center_hue(0-360), hue_range(20-120), saturation(60-100), value(30-80), speed(0.2-1.5)
               Rippling interference of sine waves — each segment independently animated.
comet          hue(0-360), saturation(0-100), value_peak(70-100), tail_length(3-8), speed(2-8)
               Bright spark bouncing left↔right with an exponential fading tail.
ripple         hue(0-360), saturation(0-100), value_min(10-50), value_max(60-100), wavelength(4-15), speed(1-5)
               Traveling brightness wave; wavelength in segments.
twinkle        base_hue(0-360), saturation(0-100), base_value(5-30), sparkle_value(70-100), rate(0.5-5)
               Dim starfield with randomly igniting and fading bright points.
ember          intensity(0.3-1.0)
               Fire simulation: left segments yellow-hot, right segments deep-red cool, all flickering.
split          hue_left(0-360), hue_right(0-360), saturation(0-100), value(20-100), split_pos(5-15), blend_width(0-5)
               Left half one color, right half another. blend_width controls crossfade zone.

━━ Hardware scenes — native device animation ━━
scene          scene_type(0=static,1=flow,2=flash,3=wave), speed(0-100), colors([[R,G,B],...] 1-7 entries 0-255)
               Example: {"pattern":"scene","scene_type":1,"speed":40,"colors":[[200,50,255],[50,200,255],[255,80,50]],"duration_sec":120}
"""

WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "icy fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "showers", 81: "heavy showers",
    95: "thunderstorm", 96: "thunderstorm with hail",
}

DEFAULT_ACTS = [
    {"pattern": "aurora", "center_hue": 240, "hue_range": 40, "saturation": 70,
     "value_center": 45, "value_range": 25, "duration_sec": 420},
]


class ExperimentEngine:
    def __init__(self, lightbar: LightbarDriver, settings: Settings):
        self._lb = lightbar
        self._settings = settings
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        self.running = False
        self._light_on = True
        self.current_experiment: Optional[Experiment] = None
        self.current_act_index: int = 0
        self.current_h: float = 0.0
        self.current_s: float = 0.0
        self.current_v: float = 0.0
        self.experiment_started_at: Optional[datetime] = None
        self.pending_prompt: Optional[str] = None
        self._abort_current = asyncio.Event()

        self.experiment_history: list[Experiment] = []
        self.log_entries: deque[LogEntry] = deque(maxlen=300)
        self._sse_queues: list[asyncio.Queue] = []
        self._task: Optional[asyncio.Task] = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self):
        self.running = True
        self._log("info", "Engine starting up")
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def inject_prompt(self, prompt: str):
        self.pending_prompt = prompt
        self._abort_current.set()
        self._log("user", f"Prompt received: {prompt}")

    def skip(self):
        """Abort current experiment and immediately generate the next one."""
        self._abort_current.set()
        self._log("user", "Skipping to next experiment")

    async def set_power(self, on: bool):
        loop = asyncio.get_event_loop()
        self._light_on = on
        if not on:
            self._abort_current.set()
            await loop.run_in_executor(None, lambda: self._lb.set_power(False))
            self._log("user", "Light turned off")
        else:
            await loop.run_in_executor(None, lambda: self._lb.set_power(True))
            self._log("user", "Light turned on")

    def subscribe_sse(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._sse_queues.append(q)
        return q

    def unsubscribe_sse(self, q: asyncio.Queue):
        try:
            self._sse_queues.remove(q)
        except ValueError:
            pass

    def get_status(self) -> EngineStatus:
        next_in = None
        if self.experiment_started_at and self.current_experiment:
            elapsed = (datetime.now(timezone.utc) - self.experiment_started_at).total_seconds()
            total = self.current_experiment.duration_minutes * 60
            next_in = max(0, int(total - elapsed))
        return EngineStatus(
            running=self.running,
            light_on=self._light_on,
            device_online=self._lb.online,
            current_experiment=self.current_experiment,
            current_step_index=self.current_act_index,
            current_hue=self.current_h,
            current_saturation=self.current_s,
            current_value=self.current_v,
            experiment_started_at=self.experiment_started_at,
            next_experiment_in_seconds=next_in,
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _loop(self):
        await self._probe_device()
        while self.running:
            if not self._light_on:
                await asyncio.sleep(1)
                continue
            self._abort_current.clear()
            experiment = await self._generate_experiment()
            if experiment:
                self.current_experiment = experiment
                self.experiment_started_at = datetime.now(timezone.utc)
                self.experiment_history.append(experiment)
                if len(self.experiment_history) > 20:
                    self.experiment_history.pop(0)
                await self._execute_experiment(experiment)
            else:
                await asyncio.sleep(30)

    # ── Device probe ──────────────────────────────────────────────────────────

    async def _probe_device(self):
        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, self._lb.get_status)
        if status:
            color_hex = status.get("24", "")
            if color_hex:
                self.current_h, self.current_s, self.current_v = tuya_to_hsv(color_hex)
            self._log("device", f"Device online — DPs: {status}")
        else:
            self._log("error", "Device unreachable on startup")

    # ── AI generation ─────────────────────────────────────────────────────────

    async def _generate_experiment(self) -> Optional[Experiment]:
        self._log("ai", "Generating next light program...")
        ctx = await self._build_context()
        user_msg = self._build_prompt(ctx)

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=self._settings.ai_model,
                    max_tokens=800,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                ),
            )
            raw = response.content[0].text.strip()
            self._log("ai", f"Response received ({len(raw)} chars)")
            return self._parse_experiment(raw, ctx.get("user_prompt"))
        except anthropic.APIError as e:
            self._log("error", f"Anthropic API error: {e}")
            return self._fallback_experiment()
        except Exception as e:
            self._log("error", f"Generation failed: {e}")
            return self._fallback_experiment()

    async def _build_context(self) -> dict:
        ctx: dict = {}
        now = datetime.now()
        ctx["time"] = now.strftime("%H:%M")
        ctx["day"] = now.strftime("%A")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = (
                    f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={self._settings.weather_lat}"
                    f"&longitude={self._settings.weather_lon}"
                    f"&current=weather_code,temperature_2m&forecast_days=1"
                )
                async with session.get(url) as r:
                    data = await r.json()
                    temp = data["current"]["temperature_2m"]
                    code = data["current"]["weather_code"]
                    desc = WEATHER_CODES.get(code, f"code {code}")
                    ctx["weather"] = f"{desc}, {temp}°C"
                    self._log("info", f"Weather: {ctx['weather']}")
        except Exception:
            ctx["weather"] = None

        ctx["recent_themes"] = [e.theme for e in self.experiment_history[-3:]]

        if self.pending_prompt:
            ctx["user_prompt"] = self.pending_prompt
            self.pending_prompt = None

        return ctx

    def _build_prompt(self, ctx: dict) -> str:
        lines = [
            f"Time: {ctx['time']}, {ctx['day']}",
        ]
        if ctx.get("weather"):
            lines.append(f"Weather: {ctx['weather']}")
        if ctx.get("recent_themes"):
            lines.append(f"Recent themes (avoid repeating): {', '.join(ctx['recent_themes'])}")
        if ctx.get("user_prompt"):
            lines.append(f"Human direction: {ctx['user_prompt']}")

        return f"""{chr(10).join(lines)}

{PATTERN_CATALOG}

Compose a light program as a JSON object:
{{
  "theme": "evocative short name",
  "inspiration": "one phrase",
  "description": "one sentence — what the viewer sees",
  "duration_minutes": 7,
  "acts": [
    {{"pattern": "aurora", "center_hue": 160, "hue_range": 50, "saturation": 85, "value_center": 55, "value_range": 30, "duration_sec": 120}},
    {{"pattern": "breathe", "hue": 200, "saturation": 70, "value_min": 15, "value_max": 75, "period_sec": 5, "duration_sec": 90}}
  ]
}}

Rules:
- 2-5 acts, they cycle for duration_minutes
- Each act must include "pattern" and "duration_sec" (15-180)
- Use varied patterns — mix whole-bar and segment patterns for contrast
- Segment patterns (gradient, plasma, comet, ripple, twinkle, ember, split) update slowly — good for sustained ambience; pair them with a faster whole-bar act
- palette_cycle: hues must be a JSON array of numbers e.g. "hues": [15, 120, 240]
- Be dramatic, evocative, unexpected
- No newlines inside string values"""

    def _parse_experiment(self, raw: str, user_prompt: Optional[str]) -> Optional[Experiment]:
        try:
            text = raw.strip()
            # Strip markdown fences
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else parts[0]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            # Sanitise literal newlines inside JSON string values
            text = re.sub(
                r'"(.*?)"',
                lambda m: '"' + m.group(1).replace('\n', ' ').replace('\r', '') + '"',
                text,
                flags=re.DOTALL,
            )
            data = json.loads(text)

            acts = data.get("acts", [])
            if not acts:
                raise ValueError("No acts in response")

            exp = Experiment(
                id=str(uuid.uuid4())[:8],
                theme=data["theme"],
                inspiration=data["inspiration"],
                description=data["description"],
                duration_minutes=max(4, min(15, int(data.get("duration_minutes", 7)))),
                acts=acts,
                created_at=datetime.now(timezone.utc),
                prompted_by=user_prompt,
            )
            act_names = ", ".join(a.get("pattern", "?") for a in acts)
            self._log(
                "ai",
                f'New program: "{exp.theme}" [{act_names}] — {exp.description}',
                {"inspiration": exp.inspiration, "acts": len(acts), "duration": exp.duration_minutes},
            )
            return exp
        except Exception as e:
            self._log("error", f"Parse failed: {e} | raw: {raw[:300]}")
            return None

    def _fallback_experiment(self) -> Experiment:
        self._log("info", "Using fallback (aurora drift)")
        return Experiment(
            id="fallback",
            theme="aurora drift",
            inspiration="fallback — AI unavailable",
            description="A slow organic drift through deep blues and purples.",
            duration_minutes=self._settings.experiment_interval_minutes,
            acts=DEFAULT_ACTS,
            created_at=datetime.now(timezone.utc),
        )

    # ── Execution ─────────────────────────────────────────────────────────────

    async def _execute_experiment(self, experiment: Experiment):
        duration_sec = experiment.duration_minutes * 60
        started = asyncio.get_event_loop().time()
        acts = experiment.acts
        act_count = len(acts)

        self._log("device", f'Running "{experiment.theme}" — {act_count} acts, {experiment.duration_minutes} min')

        act_idx = 0
        while True:
            elapsed = asyncio.get_event_loop().time() - started
            if elapsed >= duration_sec:
                break
            if self._abort_current.is_set():
                self._log("info", "Interrupted by user prompt")
                break

            act = acts[act_idx % act_count]
            self.current_act_index = act_idx % act_count
            act_dur = float(act.get("duration_sec", 60))
            pattern_name = act.get("pattern", "drift")

            self._log("device", f'Act {self.current_act_index + 1}/{act_count}: {pattern_name}',
                      {k: v for k, v in act.items() if k not in ("pattern", "duration_sec")})

            await self._run_act(act, min(act_dur, duration_sec - elapsed))

            act_idx += 1

        self._log("info", f'"{experiment.theme}" complete')

    async def _run_segment_act(self, act: dict, duration_sec: float):
        """Run a segment pattern. Each frame updates all 20 LEDs (~4s per sweep)."""
        loop = asyncio.get_event_loop()
        pattern_name = act.get("pattern", "gradient")
        params = {k: v for k, v in act.items() if k not in ("pattern", "duration_sec")}
        act_start = loop.time()
        state = None

        while True:
            t = loop.time() - act_start
            if t >= duration_sec or self._abort_current.is_set():
                break

            segments, state = pat.evaluate_segments(pattern_name, t, params, state)

            # Expose midpoint segment as current HSV for the status API
            mid = next((s for s in segments[8:12] if s is not None), None)
            if mid:
                self.current_h, self.current_s, self.current_v = mid

            # Blocking sweep (~4s); no additional sleep needed
            await loop.run_in_executor(
                None, lambda s=segments: self._lb.set_all_segments(s, segment_delay=0.20)
            )

    async def _run_act(self, act: dict, duration_sec: float):
        """Run a single act for up to duration_sec seconds."""
        loop = asyncio.get_event_loop()
        pattern_name = act.get("pattern", "drift")

        # ── Segment pattern — 20 individual LEDs via set_all_segments ─────────
        if pattern_name in SEGMENT_PATTERNS:
            await self._run_segment_act(act, duration_sec)
            return

        # ── Hardware scene — send once, device animates natively ──────────────
        if pattern_name == "scene":
            scene_type = int(act.get("scene_type", 1))
            speed = int(act.get("speed", 40))
            colors = [tuple(c) for c in act.get("colors", [[255, 255, 255]])]
            await loop.run_in_executor(
                None, lambda: self._lb.set_scene(scene_type, speed, colors)
            )
            # Hold for duration, checking for abort every tick
            elapsed = 0.0
            while elapsed < duration_sec:
                if self._abort_current.is_set():
                    return
                await asyncio.sleep(TICK)
                elapsed += TICK
            return

        # ── Software pattern — compute HSV at 10 Hz ───────────────────────────
        params = {k: v for k, v in act.items() if k not in ("pattern", "duration_sec")}
        act_start = loop.time()
        state = None
        prev_h, prev_s, prev_v = self.current_h, self.current_s, self.current_v
        crossfade_dur = min(1.5, duration_sec * 0.15)

        while True:
            now = loop.time()
            t = now - act_start
            if t >= duration_sec:
                break
            if self._abort_current.is_set():
                return

            (h, s, v), state = pat.evaluate(pattern_name, t, params, state)
            h = max(0.0, min(360.0, h))
            s = max(0.0, min(100.0, s))
            v = max(0.0, min(100.0, v))

            if t < crossfade_dur:
                frac = t / crossfade_dur
                dh = h - prev_h
                if dh > 180:
                    dh -= 360
                elif dh < -180:
                    dh += 360
                h = (prev_h + dh * frac) % 360
                s = prev_s + (s - prev_s) * frac
                v = prev_v + (v - prev_v) * frac

            self.current_h, self.current_s, self.current_v = h, s, v
            await loop.run_in_executor(None, lambda hh=h, ss=s, vv=v: self._lb.set_color(hh, ss, vv))
            await asyncio.sleep(TICK)

    # ── Logging / SSE ─────────────────────────────────────────────────────────

    def _log(self, level: str, message: str, data: Optional[dict] = None):
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            data=data,
        )
        self.log_entries.append(entry)
        logger.info(f"[{level.upper()}] {message}")
        payload = entry.model_dump_json()
        for q in list(self._sse_queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


def _lerp_hue(h1: float, h2: float, t: float) -> float:
    diff = h2 - h1
    if diff > 180:
        diff -= 360
    elif diff < -180:
        diff += 360
    return (h1 + diff * t) % 360
