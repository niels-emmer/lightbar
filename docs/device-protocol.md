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
