"""
sniff.py — Passive DP monitor for the Battletron lightbar.

Opens a persistent TCP connection to the device and listens for unsolicited
state broadcasts.  Use the Tuya app to make changes while this runs; every
DP delta is printed with a timestamp so you can map unknown DPs.

Usage:
    cd backend
    .venv/bin/python sniff.py

Press Ctrl+C to stop.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

import tinytuya
from dotenv import load_dotenv

# ── credentials ──────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

DEVICE_ID  = os.environ["DEVICE_ID"]
DEVICE_IP  = os.environ["DEVICE_IP"]
DEVICE_KEY = os.environ["DEVICE_KEY"]
VERSION    = float(os.getenv("DEVICE_VERSION", "3.5"))

# ── formatting ───────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
RED    = "\033[31m"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def fmt_dp(dp: str, val) -> str:
    """Pretty-print a single DP value."""
    # Hint at known DPs
    labels = {
        "20": "power",
        "21": "mode",
        "24": "color_hsv",
        "26": "?26",
        "46": "?46",
        "47": "?47",
        "51": "scene_data",
        "53": "?53",
    }
    label = labels.get(str(dp), f"?{dp}")
    return f"  DP {dp:>3} ({label:<12}) = {BOLD}{val!r}{RESET}"


def print_diff(prev: dict, curr: dict) -> None:
    """Print only the DPs that changed between two status snapshots."""
    all_keys = sorted(set(prev) | set(curr), key=lambda k: int(k) if str(k).isdigit() else 9999)
    changed = [k for k in all_keys if prev.get(k) != curr.get(k)]
    if not changed:
        return

    print(f"\n{YELLOW}[{ts()}] ── {len(changed)} DP(s) changed ──{RESET}")
    for k in changed:
        old = prev.get(k, "<absent>")
        new = curr.get(k, "<absent>")
        print(f"  DP {k:>3}  {RED}{old!r}{RESET}  →  {GREEN}{BOLD}{new!r}{RESET}")


def print_full(dps: dict, label: str = "status") -> None:
    """Print all DPs (used for the initial snapshot)."""
    print(f"\n{CYAN}[{ts()}] ── {label} ──{RESET}")
    for k in sorted(dps, key=lambda x: int(x) if str(x).isdigit() else 9999):
        print(fmt_dp(k, dps[k]))


# ── main loop ─────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"{BOLD}Lightbar DP sniffer{RESET}  (device {DEVICE_IP}  proto v{VERSION})")
    print("Use the Tuya app to make changes.  Ctrl+C to quit.\n")

    d = tinytuya.BulbDevice(
        dev_id=DEVICE_ID,
        address=DEVICE_IP,
        local_key=DEVICE_KEY,
        version=VERSION,
    )
    d.set_socketPersistent(True)
    d.set_socketTimeout(2)        # short poll interval
    d.set_socketRetryLimit(3)

    # ── initial snapshot (retry until device is reachable) ──
    last_dps: dict = {}
    while True:
        try:
            snap = d.status()
            if snap and "dps" in snap:
                last_dps = {str(k): v for k, v in snap["dps"].items()}
                print_full(last_dps, "initial snapshot")
                break
            else:
                print(f"[{ts()}] {YELLOW}device unreachable, retrying in 5 s… ({snap.get('Error','?')}){RESET}")
                time.sleep(5)
        except KeyboardInterrupt:
            print(f"\n{BOLD}Stopped.{RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"[{ts()}] {YELLOW}device unreachable, retrying in 5 s… ({e}){RESET}")
            time.sleep(5)

    print(f"\n{BOLD}Listening for changes…{RESET}")

    # ── listen loop ──
    consecutive_errors = 0
    while True:
        try:
            data = d.receive()

            if data is None:
                # timeout — no packet, keep looping
                consecutive_errors = 0
                continue

            if isinstance(data, dict) and "Error" in data:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    print(f"{RED}[{ts()}] too many errors, reconnecting…{RESET}")
                    time.sleep(2)
                    d.set_socketPersistent(True)   # reconnect
                    consecutive_errors = 0
                continue

            consecutive_errors = 0

            # extract DPs
            dps_raw = None
            if isinstance(data, dict):
                dps_raw = data.get("dps") or (data.get("payload") or {}).get("dps")
            if not dps_raw:
                # show raw for debugging
                print(f"[{ts()}] raw: {data}")
                continue

            new_dps = {str(k): v for k, v in dps_raw.items()}

            # merge into full known state & show diff
            merged = {**last_dps, **new_dps}
            print_diff(last_dps, merged)
            last_dps = merged

        except KeyboardInterrupt:
            print(f"\n{BOLD}Stopped.{RESET}")
            break
        except Exception as e:
            print(f"[{ts()}] {RED}exception: {e}{RESET}")
            time.sleep(1)


if __name__ == "__main__":
    main()
