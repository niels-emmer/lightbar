# DP Map — Battletron Gaming Light Bar (Tuya v3.5)

Device: Battletron Gaming Light Bar (credentials in `.env`)

## Confirmed DPs

| DP | Function | Type | Range / Values | Notes |
|----|----------|------|----------------|-------|
| 20 | Power | bool | `True` / `False` | |
| 21 | Mode | string | `'colour'` / `'white'` / `'scene'` | Must be `'colour'` for DP 24 **and** for DP 61 (device silently discards DP 61 in `'scene'` mode) |
| 24 | Color HSV (whole bar) | string | 12-char hex `HHHHSSSSVVVV` | Each component 0–1000 as 4-digit hex; hue is raw 0–360 |
| 61 | Per-segment colour | string | base64, 13 bytes | **New — see full spec below** |

## DP 61 — Per-segment colour control (discovered 2026-04-11)

### Summary

DP 61 controls one LED segment at a time. The lightbar has **20 segments** (indexed 1–20,
left to right). Sending a DP 61 command affects only the targeted segment; all other
segments remain unchanged. DP 21 must be set to **`'colour'`** before writing DP 61 — the device silently discards DP 61 payloads when DP 21 is `'scene'`.

### How it was discovered

Passive TCP sniffing of port 6668 using `backend/sniff.py` while manually toggling
each segment on (red 100%) then off in the Tuya app. All 20 on-commands and 19 off-commands
were captured and decoded. See `records/experiment-log.md` for session notes.

### Payload format

The value is a **base64-encoded 13-byte binary string**.

```
Byte  Value      Meaning
────  ─────────  ──────────────────────────────────────────────
 0    0x00       Reserved (always 0)
 1    0x01       Always 1 (bar power-on flag)
 2    0x00       Reserved (always 0)
 3    0x14 (20)  Total segment count — hardcoded 20 for this bar
 4    0x01/0x02  Mode: 0x01 = solid colour ON, 0x02 = OFF/black
 5–6  uint16 BE  Hue, 0–360 (raw degrees, same scale as DP 24)
 7–8  uint16 BE  Saturation, 0–1000 (100% = 1000)
 9–10 uint16 BE  Value/Brightness, 0–1000 (100% = 1000)
11    0x81       Unknown flag — always 0x81, do not change
12    1–20       Segment index (1-based, left to right)
```

### Python helpers (also in `backend/lightbar.py`)

```python
import base64

def segment_on_payload(segment: int, h: float, s: float, v: float) -> str:
    """segment 1-20, h 0-360, s 0-100, v 0-100"""
    hh = int(max(0, min(360, h)))
    ss = int(max(0, min(1000, s * 10)))
    vv = int(max(0, min(1000, v * 10)))
    data = bytes([
        0x00, 0x01, 0x00, 0x14, 0x01,
        (hh >> 8) & 0xFF, hh & 0xFF,
        (ss >> 8) & 0xFF, ss & 0xFF,
        (vv >> 8) & 0xFF, vv & 0xFF,
        0x81, max(1, min(20, segment)),
    ])
    return base64.b64encode(data).decode()

def segment_off_payload(segment: int) -> str:
    data = bytes([0x00, 0x01, 0x00, 0x14, 0x02,
                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                  0x81, max(1, min(20, segment))])
    return base64.b64encode(data).decode()
```

### Usage

```python
# Set segment 5 to pure green
d.set_value(21, "colour")   # NOTE: 'colour' not 'scene' — device ignores DP 61 in scene mode
d.set_value(61, segment_on_payload(5, h=120, s=100, v=100))

# Turn off segment 5
d.set_value(61, segment_off_payload(5))
```

### Verified sample payloads

| Segment | Action | Base64 payload |
|---------|--------|----------------|
| 1 | ON red 100% | `AAEAFAEAAAPoA+iBAQ==` |
| 10 | ON red 100% | `AAEAFAEAAAPoA+iBCg==` |
| 20 | ON red 100% | `AAEAFAEAAAPoA+iBFA==` |
| 1 | OFF | `AAEAFAIAAAAAAACBAQ==` |
| 20 | OFF | `AAEAFAIAAAAAAACBFA==` |

## Unknown DPs (observed values)

| DP | Observed | Hypothesis |
|----|----------|------------|
| 26 | `0` | Unknown — possibly scene index or effect selector |
| 46 | `39` | Possibly scene speed or effect parameter |
| 47 | `33` | Possibly brightness offset or effect variant |
| 53 | `33` | Possibly another effect parameter |

## Mapping notes

To map an unknown DP:
1. Read `status()` before any change.
2. Change one parameter in the Tuya app.
3. Read `status()` again.
4. Record the delta here.

DPs 46/47/53 may relate to the `scene` mode (DP 21 = `'scene'`). Not yet explored.
