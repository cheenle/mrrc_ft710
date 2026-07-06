#!/usr/bin/env python3
"""Test each audio device with timeout. No fork, no CoreFoundation crash."""
import pyaudio
import signal
import sys
import os

# Only test these devices (skip the ones we know hang)
# [0] PCM1794X2 BT5.1 out only
# [1] VA2462-2K-HD out only
# [2] USB Audio CODEC out only
# [3] USB Audio CODEC in=2 ← likely FT-710!
# [4] USB Audio Device in=1 → KNOWN TO HANG
# [5] USB PnP Sound Device in=1 → KNOWN TO HANG
# [6] BlackHole 2ch virtual
# [8] FT8 virtual
TEST_DEVICES = [3, 6, 8]

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Timed out")

p = pyaudio.PyAudio()

for idx in TEST_DEVICES:
    info = p.get_device_info_by_index(idx)
    name = info['name']
    ch = info['maxInputChannels']
    rate = int(info['defaultSampleRate'])
    print(f"[{idx}] {name} in={ch} rate={rate}...", end=" ", flush=True)
    
    if ch <= 0:
        print("SKIP (no input)")
        continue
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(4)
    try:
        s = p.open(
            format=pyaudio.paInt16,
            channels=min(ch, 2),
            rate=rate,
            input=True,
            input_device_index=idx,
            frames_per_buffer=480
        )
        signal.alarm(0)
        s.close()
        print("OK!")
    except TimeoutError:
        print("HANG")
    except Exception as e:
        signal.alarm(0)
        print(f"FAIL: {e}")

p.terminate()
print("\nDone.")
