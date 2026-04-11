"""
Pattern generators — pure math functions that return (h, s, v) at time t (seconds).

Stateless patterns: call with t each tick.
Stateful patterns: instantiate a class, call .tick(t) each tick.

All output: h 0-360, s 0-100, v 0-100.
"""

import math
import random
from dataclasses import dataclass, field


# ── Stateless patterns ────────────────────────────────────────────────────────

def breathe(t: float, hue: float, saturation: float,
            value_min: float, value_max: float, period_sec: float = 4.0) -> tuple[float, float, float]:
    """Smooth sine-wave oscillation on brightness. Inhale/exhale rhythm."""
    v = value_min + (value_max - value_min) * (1 - math.cos(2 * math.pi * t / period_sec)) / 2
    return hue, saturation, v


def wheel(t: float, saturation: float, value: float,
          start_hue: float = 0.0, deg_per_sec: float = 30.0) -> tuple[float, float, float]:
    """Continuous hue rotation. Full cycle = 360/deg_per_sec seconds."""
    h = (start_hue + deg_per_sec * t) % 360
    return h, saturation, value


def pulse(t: float, hue: float, saturation: float,
          value_peak: float = 90.0, period_sec: float = 2.0) -> tuple[float, float, float]:
    """Sharp attack, exponential decay — like a heartbeat or muzzle flash."""
    phase = (t % period_sec) / period_sec
    attack = 0.08
    if phase < attack:
        v = value_peak * (phase / attack)
    else:
        v = value_peak * math.exp(-7 * (phase - attack) / (1 - attack))
    return hue, saturation, max(0.0, v)


def strobe(t: float, hue: float, saturation: float,
           value: float = 90.0, rate_hz: float = 4.0, duty: float = 0.5) -> tuple[float, float, float]:
    """Hard on/off flash at rate_hz. duty 0-1 = fraction of period that is ON."""
    on = (t * rate_hz) % 1.0 < duty
    return hue, saturation, value if on else 0.0


def aurora(t: float, center_hue: float, hue_range: float,
           saturation: float, value_center: float, value_range: float) -> tuple[float, float, float]:
    """
    Multi-frequency sine superposition — organic, unpredictable shimmer.
    Uses 3 incommensurate frequencies for hue and 3 for value so it never
    exactly repeats within a normal session.
    """
    h = (center_hue
         + hue_range * math.sin(t * 0.113)
         + hue_range * 0.45 * math.sin(t * 0.177 + 1.31)
         + hue_range * 0.2 * math.sin(t * 0.293 + 2.71)) % 360
    v = (value_center
         + value_range * math.sin(t * 0.131 + 0.5)
         * (0.6 + 0.4 * math.sin(t * 0.211 + 1.73)))
    return h, saturation, max(0.0, min(100.0, v))


def lfo_pair(t: float,
             hue_a: float, hue_b: float, saturation: float,
             value: float, period_sec: float = 8.0) -> tuple[float, float, float]:
    """
    Morphs smoothly between two hues on a cosine curve.
    Simple but effective for dramatic color transitions.
    """
    frac = (1 - math.cos(2 * math.pi * t / period_sec)) / 2  # 0→1→0
    dh = hue_b - hue_a
    if dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    h = (hue_a + dh * frac) % 360
    return h, saturation, value


# ── Stateful patterns ─────────────────────────────────────────────────────────

class ThunderState:
    """
    Mostly dark with random lightning flashes.
    Flash timing is stochastic — each flash is independently scheduled.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._flash_events: list[tuple[float, float]] = []  # (start, end) pairs
        self._last_schedule_t: float = -1.0

    def _schedule_flashes(self, t: float, flash_rate_per_min: float):
        """Pre-schedule the next 10 seconds of flashes."""
        horizon = t + 10.0
        if self._flash_events and self._flash_events[-1][1] > t + 5.0:
            return  # still have plenty ahead
        avg_gap = 60.0 / flash_rate_per_min
        cur = t if not self._flash_events else self._flash_events[-1][1]
        while cur < horizon:
            gap = self._rng.uniform(avg_gap * 0.3, avg_gap * 2.0)
            cur += gap
            dur = self._rng.uniform(0.04, 0.18)
            # Sometimes a double-flash
            if self._rng.random() < 0.3:
                self._flash_events.append((cur, cur + dur * 0.5))
                cur += dur * 0.5 + self._rng.uniform(0.05, 0.15)
                dur = self._rng.uniform(0.04, 0.12)
            self._flash_events.append((cur, cur + dur))

    def tick(self, t: float, bg_hue: float = 230.0, bg_saturation: float = 60.0,
             bg_value: float = 8.0, flash_rate_per_min: float = 12.0) -> tuple[float, float, float]:
        self._schedule_flashes(t, flash_rate_per_min)
        # Clean old events
        self._flash_events = [(s, e) for s, e in self._flash_events if e > t - 0.5]
        # Check if we're in a flash
        for start, end in self._flash_events:
            if start <= t <= end:
                progress = (t - start) / max(0.001, end - start)
                # Sharp rise, fast fade
                if progress < 0.15:
                    intensity = progress / 0.15
                else:
                    intensity = 1.0 - (progress - 0.15) / 0.85
                intensity = max(0.0, intensity)
                # Flash is cool white-blue
                return 220.0, 15.0, 20.0 + 75.0 * intensity
        return bg_hue, bg_saturation, bg_value


class CampfireState:
    """
    Warm flickering fire. Red/orange/amber with randomised flicker.
    Uses multiple overlapping low-frequency oscillators + noise.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        # Random phase offsets for the oscillator bank
        self._phases = [self._rng.uniform(0, 2 * math.pi) for _ in range(5)]
        self._freqs = [0.7, 1.3, 2.1, 3.7, 5.3]  # Hz
        self._amps = [0.35, 0.25, 0.20, 0.12, 0.08]

    def tick(self, t: float, intensity: float = 0.8) -> tuple[float, float, float]:
        # Base: warm orange-red
        base_hue = 18.0
        base_sat = 95.0
        base_val = 55.0 * intensity

        # Flicker: sum of oscillators
        flicker = sum(
            a * math.sin(2 * math.pi * f * t + p)
            for a, f, p in zip(self._amps, self._freqs, self._phases)
        )
        # Map flicker to hue shift (redder when dim, oranger when bright)
        hue_shift = flicker * 15.0
        val_shift = flicker * 30.0 * intensity

        h = max(0.0, min(360.0, base_hue + hue_shift))
        s = base_sat
        v = max(5.0, min(100.0, base_val + val_shift))
        return h, s, v


class DriftState:
    """
    Slow random walk through HSV space. Targets shift gradually,
    giving an organic, generative feel without repeating.
    """

    def __init__(self, hue: float, saturation: float, value: float, seed: int | None = None):
        self._rng = random.Random(seed)
        self.h = hue
        self.s = saturation
        self.v = value
        self._th = hue       # target hue
        self._tv = value     # target value
        self._next_retarget = 0.0

    def tick(self, t: float, hue_drift: float = 40.0,
             value_drift: float = 25.0, speed: float = 0.5) -> tuple[float, float, float]:
        if t >= self._next_retarget:
            self._th = (self.h + self._rng.uniform(-hue_drift, hue_drift)) % 360
            self._tv = max(15.0, min(90.0, self.v + self._rng.uniform(-value_drift, value_drift)))
            self._next_retarget = t + self._rng.uniform(3.0, 8.0) / speed

        # Smooth move towards target (exponential approach)
        dh = self._th - self.h
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
        step = speed * 0.05  # per 50ms tick scaled by caller
        self.h = (self.h + dh * step * 0.8) % 360
        self.v += (self._tv - self.v) * step * 0.6
        return self.h, self.s, self.v


class PaletteCycleState:
    """
    Dwells on each hue in a list then cross-fades to the next.
    AI provides the hue list; Python handles timing and interpolation.
    """

    def tick(self, t: float, hues: list[float], saturation: float,
             value: float, dwell_sec: float = 5.0) -> tuple[float, float, float]:
        if not hues:
            return 0.0, saturation, value
        n = len(hues)
        cycle_t = t % (n * dwell_sec)
        idx = int(cycle_t / dwell_sec)
        frac = (cycle_t % dwell_sec) / dwell_sec
        h1 = float(hues[idx % n])
        h2 = float(hues[(idx + 1) % n])
        crossfade_start = 0.75
        if frac < crossfade_start:
            h = h1
        else:
            blend = (frac - crossfade_start) / (1.0 - crossfade_start)
            dh = h2 - h1
            if dh > 180:
                dh -= 360
            elif dh < -180:
                dh += 360
            h = (h1 + dh * blend) % 360
        return h, saturation, value


class GlitchState:
    """
    Steady base color interrupted by brief random color spikes —
    like a signal dropout or screen tear.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._glitch_end = -1.0
        self._glitch_h = 0.0
        self._last_t = 0.0

    def tick(self, t: float, base_hue: float, saturation: float,
             value: float, glitch_rate: float = 1.5,
             glitch_duration: float = 0.12) -> tuple[float, float, float]:
        dt = t - self._last_t
        self._last_t = t
        if t > self._glitch_end and self._rng.random() < glitch_rate * dt:
            self._glitch_end = t + self._rng.uniform(0.5, 2.0) * glitch_duration
            self._glitch_h = (base_hue + self._rng.choice([60, 120, 180, 240, 300])) % 360
        if t <= self._glitch_end:
            return self._glitch_h, min(100.0, saturation + 20), min(100.0, value + 15)
        return base_hue, saturation, value


# ── Segment patterns (return list[tuple|None] of length NSEG) ─────────────────

NSEG = 20

SEGMENT_PATTERNS = {"gradient", "comet", "plasma", "ripple", "twinkle", "ember", "split"}


def gradient(t: float, hue_left: float, hue_right: float,
             saturation: float, value: float,
             speed: float = 5.0) -> list:
    """
    Linear hue gradient across all 20 segments.
    speed (deg/sec) scrolls the gradient over time — 0 = static.
    """
    offset = speed * t
    dh = hue_right - hue_left
    if dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    result = []
    for i in range(NSEG):
        frac = i / (NSEG - 1)
        h = (hue_left + dh * frac + offset) % 360
        result.append((h, saturation, value))
    return result


def comet(t: float, hue: float, saturation: float,
          value_peak: float = 90.0, tail_length: int = 5,
          speed: float = 4.0) -> list:
    """
    Bright spark bouncing left↔right with an exponential fade tail.
    speed is segments per second.
    """
    travel = NSEG - 1  # 19 positions
    period = 2.0 * travel / max(0.1, speed)
    pos_t = t % period
    if pos_t < period / 2:
        head = pos_t * speed
    else:
        head = 2.0 * travel - pos_t * speed

    result = []
    for i in range(NSEG):
        dist = head - i  # positive = tail behind head
        if 0.0 <= dist <= tail_length:
            intensity = math.exp(-3.5 * dist / max(1, tail_length))
            result.append((hue, saturation, max(2.0, value_peak * intensity)))
        else:
            result.append(None)
    return result


def plasma(t: float, center_hue: float, hue_range: float,
           saturation: float, value: float,
           speed: float = 0.5) -> list:
    """
    Rippling interference pattern — each segment gets a phase-shifted
    combination of two incommensurate sine waves, producing organic motion
    that never quite repeats.
    """
    result = []
    for i in range(NSEG):
        phase = i * 0.62  # irrational spatial phase between segments
        h = (center_hue
             + hue_range * math.sin(t * speed + phase)
             + hue_range * 0.4 * math.sin(t * speed * 1.73 + phase * 1.31)) % 360
        v = value * (0.55 + 0.45 * math.sin(t * speed * 0.89 + phase * 0.77))
        result.append((h, saturation, max(5.0, min(100.0, v))))
    return result


def ripple(t: float, hue: float, saturation: float,
           value_min: float, value_max: float,
           wavelength: float = 8.0, speed: float = 3.0) -> list:
    """
    Traveling sine wave of brightness across the bar.
    wavelength is in segments; speed is segments per second.
    """
    result = []
    for i in range(NSEG):
        phase = 2.0 * math.pi * (i / wavelength - t * speed / wavelength)
        v = value_min + (value_max - value_min) * (1.0 + math.sin(phase)) / 2.0
        result.append((hue, saturation, v))
    return result


def split(t: float, hue_left: float, hue_right: float,
          saturation: float, value: float,
          split_pos: float = 10.0, blend_width: float = 3.0) -> list:
    """
    Two-zone color split with an optional blend region in the middle.
    split_pos: segment index (0-19) where the right color takes over.
    blend_width: number of segments for the crossfade zone (0 = hard cut).
    """
    result = []
    dh = hue_right - hue_left
    if dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    for i in range(NSEG):
        if blend_width <= 0:
            frac = 1.0 if i >= split_pos else 0.0
        else:
            frac = max(0.0, min(1.0, (i - split_pos + blend_width / 2) / blend_width))
        h = (hue_left + dh * frac) % 360
        result.append((h, saturation, value))
    return result


class TwinkleState:
    """
    Starfield — most segments hold a dim base; random ones ignite
    and fade in a smooth arc. Rate is new sparkles per second.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._sparkles: dict[int, tuple[float, float]] = {}  # seg -> (start_t, duration)
        self._last_t = 0.0

    def tick(self, t: float, base_hue: float, saturation: float,
             base_value: float, sparkle_value: float = 90.0,
             rate: float = 2.0) -> list:
        dt = t - self._last_t
        self._last_t = t

        # Poisson arrivals
        expected = rate * max(dt, 0.0)
        n_new = int(expected) + (1 if self._rng.random() < (expected % 1.0) else 0)
        for _ in range(n_new):
            seg = self._rng.randint(0, NSEG - 1)
            self._sparkles[seg] = (t, self._rng.uniform(3.0, 9.0))

        result = []
        done = []
        for i in range(NSEG):
            if i in self._sparkles:
                start, dur = self._sparkles[i]
                elapsed = t - start
                if elapsed >= dur:
                    done.append(i)
                    result.append((base_hue, saturation, base_value))
                else:
                    progress = elapsed / dur
                    intensity = math.sin(math.pi * progress)  # 0 → peak → 0
                    v = base_value + (sparkle_value - base_value) * intensity
                    h = (base_hue + 20.0 * intensity) % 360
                    result.append((h, saturation, v))
            else:
                result.append((base_hue, saturation, base_value))
        for i in done:
            del self._sparkles[i]
        return result


class EmberState:
    """
    Fire simulation along the bar. Left segments are hottest;
    heat dissipates rightward with per-segment flicker noise.
    Colors map from deep red (cold) through orange to yellow-white (hot).
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        # Independent oscillator bank per segment for flicker
        self._phases = [
            [self._rng.uniform(0, 2 * math.pi) for _ in range(5)]
            for _ in range(NSEG)
        ]
        self._freqs = [0.7, 1.3, 2.1, 3.7, 5.3]
        self._amps = [0.30, 0.22, 0.18, 0.10, 0.07]

    def tick(self, t: float, intensity: float = 0.8) -> list:
        result = []
        for i in range(NSEG):
            # Heat gradient: segment 0 = full heat, segment 19 = ~40% heat
            heat_base = intensity * (1.0 - i / NSEG * 0.6)
            flicker = sum(
                a * math.sin(2 * math.pi * f * t + p)
                for a, f, p in zip(self._amps, self._freqs, self._phases[i])
            )
            heat = max(0.05, min(1.0, heat_base + flicker * 0.25))

            # Color map: cold = deep red (hue 0), hot = orange-yellow (hue 40)
            hue = heat * 40.0
            sat = 100.0 - heat * 15.0
            val = heat * 88.0
            result.append((hue, sat, val))
        return result


# ── Dispatchers ───────────────────────────────────────────────────────────────

def evaluate(pattern_name: str, t: float, params: dict,
             state: object | None = None) -> tuple[tuple[float, float, float], object | None]:
    """
    Evaluate a named pattern at time t with given params.
    Returns ((h, s, v), state) — state is None for stateless patterns.
    """
    p = pattern_name.lower()

    if p == "breathe":
        return breathe(t, **_pick(params, "hue", "saturation", "value_min", "value_max",
                                  period_sec=4.0)), None

    if p == "wheel":
        return wheel(t, **_pick(params, "saturation", "value",
                                start_hue=0.0, deg_per_sec=30.0)), None

    if p == "pulse":
        return pulse(t, **_pick(params, "hue", "saturation",
                                value_peak=90.0, period_sec=2.0)), None

    if p == "strobe":
        return strobe(t, **_pick(params, "hue", "saturation",
                                 value=90.0, rate_hz=4.0, duty=0.5)), None

    if p == "aurora":
        return aurora(t, **_pick(params, "center_hue", "hue_range", "saturation",
                                 "value_center", "value_range")), None

    if p == "lfo_pair":
        return lfo_pair(t, **_pick(params, "hue_a", "hue_b", "saturation",
                                   "value", period_sec=8.0)), None

    if p == "thunder":
        st = state if isinstance(state, ThunderState) else ThunderState()
        hsv = st.tick(t, **_pick(params, bg_hue=230.0, bg_saturation=60.0,
                                  bg_value=8.0, flash_rate_per_min=12.0))
        return hsv, st

    if p == "campfire":
        st = state if isinstance(state, CampfireState) else CampfireState()
        hsv = st.tick(t, **_pick(params, intensity=0.8))
        return hsv, st

    if p == "drift":
        if not isinstance(state, DriftState):
            state = DriftState(
                hue=params.get("hue", 200.0),
                saturation=params.get("saturation", 75.0),
                value=params.get("value", 55.0),
            )
        hsv = state.tick(t, **_pick(params, hue_drift=40.0, value_drift=25.0, speed=0.5))
        return hsv, state

    if p == "palette_cycle":
        st = state if isinstance(state, PaletteCycleState) else PaletteCycleState()
        hsv = st.tick(t, **_pick(params, "hues", saturation=80.0, value=70.0, dwell_sec=5.0))
        return hsv, st

    if p == "glitch":
        st = state if isinstance(state, GlitchState) else GlitchState()
        hsv = st.tick(t, **_pick(params, "base_hue", "saturation", "value",
                                  glitch_rate=1.5, glitch_duration=0.12))
        return hsv, st

    # Unknown pattern — dim violet fallback
    return (280.0, 60.0, 30.0), None


def evaluate_segments(
    pattern_name: str, t: float, params: dict, state: object | None = None
) -> tuple[list, object | None]:
    """
    Evaluate a segment pattern at time t.
    Returns (list_of_20_hsv_or_none, state).
    """
    p = pattern_name.lower()

    if p == "gradient":
        return gradient(t, **_pick(params, "hue_left", "hue_right", "saturation", "value",
                                   speed=5.0)), None

    if p == "comet":
        return comet(t, **_pick(params, "hue", "saturation",
                                value_peak=90.0, tail_length=5, speed=4.0)), None

    if p == "plasma":
        return plasma(t, **_pick(params, "center_hue", "hue_range", "saturation", "value",
                                 speed=0.5)), None

    if p == "ripple":
        return ripple(t, **_pick(params, "hue", "saturation", "value_min", "value_max",
                                 wavelength=8.0, speed=3.0)), None

    if p == "split":
        return split(t, **_pick(params, "hue_left", "hue_right", "saturation", "value",
                                split_pos=10.0, blend_width=3.0)), None

    if p == "twinkle":
        st = state if isinstance(state, TwinkleState) else TwinkleState()
        segs = st.tick(t, **_pick(params, "base_hue", "saturation", "base_value",
                                  sparkle_value=90.0, rate=2.0))
        return segs, st

    if p == "ember":
        st = state if isinstance(state, EmberState) else EmberState()
        segs = st.tick(t, **_pick(params, intensity=0.8))
        return segs, st

    # Unknown segment pattern — all dim violet
    return [(280.0, 60.0, 30.0)] * NSEG, None


def _pick(params: dict, *required: str, **defaults) -> dict:
    """Extract keys from params, using defaults for optional ones."""
    result = {k: params[k] for k in required if k in params}
    for k, v in defaults.items():
        result[k] = params.get(k, v)
    return result
