#!/usr/bin/env python3
"""Test ONLY device 3 (USB Audio CODEC in=2) with proper signal handler."""
import pyaudio
import signal
import sys
import os

# Must be in main thread for signal to work on macOS
os.environ['PYAUDIO_SAFE_CALL'] = '1'

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Timed out")

p = pyaudio.PyAudio()

idx = 3
info = p.get_device_info_by_index(idx)
name = info['name']
ch = info['maxInputChannels']
rate = int(info['defaultSampleRate'])
print(f"[{idx}] {name} in={ch} rate={rate}...", end=" ", flush=True)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

try:
    s = p.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=rate,
        input=True,
        input_device_index=idx,
        frames_per_buffer=882
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
