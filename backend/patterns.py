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


# ── Dispatcher ────────────────────────────────────────────────────────────────

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

    # Unknown pattern — dim violet fallback
    return (280.0, 60.0, 30.0), None


def _pick(params: dict, *required: str, **defaults) -> dict:
    """Extract keys from params, using defaults for optional ones."""
    result = {k: params[k] for k in required if k in params}
    for k, v in defaults.items():
        result[k] = params.get(k, v)
    return result
