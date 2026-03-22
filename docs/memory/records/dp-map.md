# DP Map — Battletron Gaming Light Bar (Tuya v3.5)

Device: Battletron Gaming Light Bar (credentials in `.env`)

## Confirmed DPs

| DP | Function | Type | Range / Values | Notes |
|----|----------|------|----------------|-------|
| 20 | Power | bool | `True` / `False` | |
| 21 | Mode | string | `'colour'` / `'white'` / `'scene'` | Must be `'colour'` for DP 24 to work |
| 24 | Color HSV | string | 12-char hex `HHHHSSSSVVVV` | Each 0–1000 as 4-digit hex |

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
