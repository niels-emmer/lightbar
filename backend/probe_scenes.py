"""
Test writing scene data directly to DP51.
Tries the captured payload, then variations with different speed/colors.

Usage:
    cd backend && source .venv/bin/activate && python probe_scenes.py
"""
import base64, time, tinytuya

d = tinytuya.BulbDevice(
    dev_id='bf7a189fa1bb1ca5bc8eou',
    address='192.168.101.130',
    local_key='~)bWA3m}uu#t]}E0',
    version=3.5
)
d.set_socketTimeout(3)

def encode(scene_type, speed, b2, colors):
    """colors: list of (r,g,b) tuples"""
    data = bytes([scene_type, speed, b2])
    for r, g, b in colors:
        data += bytes([r, g, b])
    return base64.b64encode(data).decode()

def send_scene(payload, label):
    print(f"\n{label}")
    print(f"  payload: {payload!r}")
    # Switch to scene mode, then write DP51
    r1 = d.set_value(21, 'scene')
    time.sleep(0.3)
    r2 = d.set_value(51, payload)
    print(f"  set_value result: {r2}")
    time.sleep(4)

# ── Test 1: exact captured payload ────────────────────────────────────────────
send_scene(
    'AR4KUlLgAABkABlkACJeACxbABRkAAxk',
    "Test 1: exact captured payload (type=1, speed=30, blue gradient)"
)

# ── Test 2: same type, faster speed ───────────────────────────────────────────
send_scene(
    encode(1, 80, 10, [(82,82,224),(0,0,100),(0,25,100),(0,34,94),(0,44,91),(0,20,100),(0,12,100)]),
    "Test 2: same colors, speed=80"
)

# ── Test 3: warm sunset gradient ──────────────────────────────────────────────
send_scene(
    encode(1, 40, 10, [(224,80,20),(200,60,10),(180,100,30),(220,70,15),(240,50,5),(210,90,25),(190,110,40)]),
    "Test 3: warm sunset gradient (type=1, speed=40)"
)

# ── Test 4: type=2 (possibly flash/strobe) ────────────────────────────────────
send_scene(
    encode(2, 30, 10, [(82,82,224),(0,0,100),(0,25,100),(0,34,94),(0,44,91),(0,20,100),(0,12,100)]),
    "Test 4: type=2 (flash/strobe?)"
)

# ── Test 5: type=3 (possibly another mode) ────────────────────────────────────
send_scene(
    encode(3, 30, 10, [(82,82,224),(0,0,100),(0,25,100),(0,34,94),(0,44,91),(0,20,100),(0,12,100)]),
    "Test 5: type=3"
)

# ── Test 6: single color, type=1 (static?) ────────────────────────────────────
send_scene(
    encode(0, 0, 1, [(200,0,0)]),
    "Test 6: type=0, single red — maybe static scene?"
)

print("\nDone. What did the lightbar do?")
