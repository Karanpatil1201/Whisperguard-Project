"""Security response engine: alerts, muting, and logging (scaffold)."""

import time


def alert_user(level, message):
    print(f"ALERT [{level}] - {message}")


def mute_microphone(seconds=5):
    # Placeholder: muting mic programmatically is platform-specific.
    print(f"(Simulated) muting microphone for {seconds} seconds (no OS-level mute available)")
    time.sleep(0.01)


def try_system_mute(seconds=5):
    """Attempt to mute the system microphone using pycaw (Windows).

    Returns True if system mute was attempted successfully, False otherwise.
    This is best-effort: if pycaw or required COM interfaces are unavailable,
    the function returns False so callers can fallback to app-level mute.
    """
    try:
        # Lazy import so pycaw is optional
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities
    except Exception as e:
        print("System mute not available (pycaw/comtypes missing):", e)
        return False

    try:
        devices = AudioUtilities.GetAllDevices()
        # Try to find capture (microphone) devices
        mics = [d for d in devices if d.DataFlow == 1]  # 1 == Capture
        if not mics:
            print("No capture devices found for system mute")
            return False
        for mic in mics:
            try:
                vol = mic._ctl
                # Try set mute attribute if exists
                if hasattr(vol, "SetMute"):
                    vol.SetMute(1, None)
            except Exception:
                continue
        print("Attempted system-level microphone mute (best-effort)")
        time.sleep(seconds)
        # attempt unmute
        for mic in mics:
            try:
                vol = mic._ctl
                if hasattr(vol, "SetMute"):
                    vol.SetMute(0, None)
            except Exception:
                continue
        return True
    except Exception as e:
        print("System mute failed:", e)
        return False


def log_event(event_store, level, score, fingerprint=None):
    event = {"ts": time.time(), "level": level, "score": score, "fp": fingerprint}
    event_store.append(event)
    print("Logged event:", event)
