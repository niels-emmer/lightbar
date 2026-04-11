# Device Protocol Reference

Sourced from `tuya-setup/startingpoint.md` and tinytuya experiments.

## Device

| Field | Value |
|-------|-------|
| Name | lightbar |
| Product | Battletron Gaming Light Bar (2024) |
| Device ID | *(set in `.env`)* |
| IP | *(set in `.env`)* |
| Protocol | Tuya v3.5 |
| TCP port | 6668 |
| Ping | Does NOT respond to ICMP |

## Connection

```python
import tinytuya

d = tinytuya.BulbDevice(
    dev_id='<DEVICE_ID from .env>',
    address='<DEVICE_IP from .env>',
    local_key='<from .env>',
    version=3.5
)
d.set_socketTimeout(5)
```

## Color format (DP 24)

12-character hex string: `HHHHSSSSVVVV`
Each component: 0–1000, encoded as 4-digit hex.

```python
def hsv_to_tuya(h, s, v):
    """h: 0-360 raw, s: 0-100 (×10 → 0-1000), v: 0-100 (×10 → 0-1000)"""
    return f'{int(h):04x}{int(s * 10):04x}{int(v * 10):04x}'
```

> **Important**: hue is stored as the raw 0–360 integer, NOT scaled to 0–1000.
> Blue hue=231 → `00e7` (231 decimal). Sat/val ARE scaled: 100% → `03e8` (1000).

| Color | Hex | H | S | V |
|-------|-----|---|---|---|
| Red | `000003e803e8` | 0 | 1000 | 1000 |
| Green | `015e03e803e8` | 350 | 1000 | 1000 |
| Blue | `00e703e803e8` | 231 | 1000 | 1000 |
| Blue 50% | `00e703e801f4` | 231 | 1000 | 500 |

## Sending a color

```python
# Set mode to colour first
d.set_value(21, 'colour')
# Set color
d.set_value(24, hsv_to_tuya(hue, sat, val))
```

Or use BulbDevice helpers:
```python
d.set_colour(r, g, b)       # RGB → HSV internally, sets DP 24
d.turn_on()                 # DP 20 = True
d.turn_off()                # DP 20 = False
```

## Status response

```python
status = d.status()
# {'dps': {'20': True, '21': 'colour', '24': '000003e803e8', '26': 0, '46': 39, '47': 33, '53': 33}}
```

## Known DPs

See `docs/memory/records/dp-map.md` for full map including unknown DPs.

## Per-segment control (DP 61) — discovered 2026-04-11

The lightbar has **20 individually addressable segments** (1–20, left to right).
Each segment is controlled by writing a base64-encoded 13-byte payload to **DP 61**
while DP 21 is set to **`'colour'`**. The device silently discards DP 61 writes when DP 21 is `'scene'`.

### Payload structure

```
[0x00][0x01][0x00][0x14][MODE][H_hi][H_lo][S_hi][S_lo][V_hi][V_lo][0x81][SEG]
  ^     ^     ^     ^     ^    └──── Hue 0-360 ────┘ └─ Sat 0-1000 ─┘
  │     │     │     │     │                           └─ Val 0-1000 ─┘
  │     │     │     │     0x01 = ON  /  0x02 = OFF
  │     │     │     20 = total segment count (hardcoded)
  │     │     reserved
  │     always 1
  reserved
```

Last byte `SEG` is the 1-based segment index (1–20).
Hue, Saturation, and Value use the **same scale as DP 24** (hue raw 0–360; sat/val 0–1000).
Byte 11 is always `0x81` — do not change.

### Quick example

```python
import base64

def segment_payload(seg: int, h: int, s: int, v: int, on: bool = True) -> str:
    """seg 1-20, h 0-360, s 0-1000, v 0-1000"""
    mode = 0x01 if on else 0x02
    data = bytes([0x00, 0x01, 0x00, 0x14, mode,
                  h >> 8, h & 0xFF, s >> 8, s & 0xFF, v >> 8, v & 0xFF,
                  0x81, seg])
    return base64.b64encode(data).decode()

d.set_value(21, "colour")   # 'colour' mode required — NOT 'scene'
d.set_value(61, segment_payload(1, h=0, s=1000, v=1000))   # seg 1 → red
d.set_value(61, segment_payload(1, on=False, h=0, s=0, v=0))  # seg 1 → off
```

Use `LightbarDriver.set_segment()` / `set_segment_off()` from `backend/lightbar.py`
for the thread-safe wrapped version.
