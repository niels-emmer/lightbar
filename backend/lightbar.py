import base64
import threading
import logging

import tinytuya

logger = logging.getLogger(__name__)


def hsv_to_tuya(h: float, s: float, v: float) -> str:
    """Convert HSV (h:0-360, s:0-100, v:0-100) to Tuya 12-char hex.

    Tuya encoding: hue is raw 0-360 as 4-digit hex; sat and val are
    scaled 0-1000 (i.e. multiply by 10). Confirmed from device observations:
    blue (hue=231) → 00e7 (=231), not 0281 (=641 which scaling would give).
    """
    hh = int(max(0, min(360, h)))
    ss = int(max(0, min(1000, s * 10)))
    vv = int(max(0, min(1000, v * 10)))
    return f"{hh:04x}{ss:04x}{vv:04x}"


def tuya_to_hsv(hex_str: str) -> tuple[float, float, float]:
    """Parse Tuya 12-char hex back to HSV (h:0-360, s:0-100, v:0-100)."""
    if len(hex_str) != 12:
        return 0.0, 0.0, 0.0
    hh = int(hex_str[0:4], 16)
    ss = int(hex_str[4:8], 16)
    vv = int(hex_str[8:12], 16)
    return float(hh), ss / 10.0, vv / 10.0


class LightbarDriver:
    """Thread-safe wrapper around tinytuya BulbDevice."""

    def __init__(self, device_id: str, ip: str, local_key: str, version: float = 3.5):
        self._device_id = device_id
        self._ip = ip
        self._local_key = local_key
        self._version = version
        self._lock = threading.Lock()
        self._device: tinytuya.BulbDevice | None = None
        self._online = False

    def _connect(self) -> tinytuya.BulbDevice:
        d = tinytuya.BulbDevice(
            dev_id=self._device_id,
            address=self._ip,
            local_key=self._local_key,
            version=self._version,
        )
        d.set_socketTimeout(5)
        d.set_socketRetryLimit(1)
        return d

    def set_color(self, h: float, s: float, v: float) -> bool:
        """Set HSV color. Returns True on success."""
        hex_val = hsv_to_tuya(h, s, v)
        with self._lock:
            try:
                d = self._connect()
                # Ensure colour mode
                d.set_value(21, "colour")
                d.set_value(24, hex_val)
                self._online = True
                return True
            except Exception as e:
                logger.warning(f"Lightbar set_color failed: {e}")
                self._online = False
                return False

    def set_power(self, on: bool) -> bool:
        with self._lock:
            try:
                d = self._connect()
                d.set_value(20, on)
                self._online = True
                return True
            except Exception as e:
                logger.warning(f"Lightbar set_power failed: {e}")
                self._online = False
                return False

    def set_scene(self, scene_type: int, speed: int, colors: list[tuple[int, int, int]]) -> bool:
        """Send a hardware scene to DP51.

        scene_type: 0=static, 1=gradient/flow, 2=flash, 3=wave
        speed: 0-100
        colors: list of (r, g, b) tuples, 1-7 entries, each 0-255
        """
        data = bytes([max(0, min(3, scene_type)), max(0, min(100, speed)), 10])
        for r, g, b in colors[:7]:
            data += bytes([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))])
        payload = base64.b64encode(data).decode()
        with self._lock:
            try:
                d = self._connect()
                d.set_value(21, "scene")
                d.set_value(51, payload)
                self._online = True
                return True
            except Exception as e:
                logger.warning(f"Lightbar set_scene failed: {e}")
                self._online = False
                return False

    def get_status(self) -> dict | None:
        with self._lock:
            try:
                d = self._connect()
                status = d.status()
                self._online = True
                return status.get("dps", {})
            except Exception as e:
                logger.warning(f"Lightbar get_status failed: {e}")
                self._online = False
                return None

    @property
    def online(self) -> bool:
        return self._online
