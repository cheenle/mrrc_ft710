#!/usr/bin/env python3
"""Definitive probe (run with server STOPPED — exclusive serial + audio):

1. Measure audio level on candidate input devices [3,4,5].
2. On the device carrying radio audio, toggle the SH filter via CAT
   (widest 4000Hz vs narrow 1100Hz) and compare the captured spectrum:
   if energy above the narrow edge collapses, the IF filter provably
   reaches this audio path.
Restores the original width and prints a verdict."""
import serial
import time
import numpy as np
import pyaudio

PORT = "/dev/cu.usbserial-0121DB3A0"
BAUD = 38400
RATE = 44100
DEVICES = [3, 4, 5]

WIDE, NARROW = 23, 5   # 4000 Hz vs 1100 Hz (voice table)


# ── serial helpers ──────────────────────────────────────────────────
def read_resp(ser, prefix, timeout=0.8):
    deadline = time.monotonic() + timeout
    buf = b""
    while time.monotonic() < deadline:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            while b";" in buf:
                frame, buf = buf.split(b";", 1)
                frame = frame.decode("ascii", "replace")
                if frame.startswith(prefix):
                    return frame
        else:
            time.sleep(0.01)
    return None


def send(ser, cmd):
    ser.write((cmd + ";").encode("ascii"))


def query(ser, cmd, prefix=None):
    send(ser, cmd)
    return read_resp(ser, prefix or cmd)


# ── audio helpers ───────────────────────────────────────────────────
def capture(pa, idx, seconds):
    info = pa.get_device_info_by_index(idx)
    ch = min(2, int(info.get("maxInputChannels", 1)))
    st = pa.open(format=pyaudio.paInt16, channels=ch, rate=RATE,
                 input=True, input_device_index=idx, frames_per_buffer=1024)
    frames = []
    for _ in range(int(RATE / 1024 * seconds)):
        frames.append(st.read(1024, exception_on_overflow=False))
    st.stop_stream()
    st.close()
    x = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    return x


def band_frac(x, lo, hi):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1.0 / RATE)
    num = X[(freqs >= lo) & (freqs < hi)].sum()
    den = X[freqs >= 20].sum() + 1e-9
    return float(num / den)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0


def main():
    pa = pyaudio.PyAudio()

    # 1) which device carries audio?
    levels = {}
    for idx in DEVICES:
        try:
            x = capture(pa, idx, 2.0)
            levels[idx] = rms(x)
            print(f"[{idx}] rms={levels[idx]:9.1f}")
        except Exception as e:
            print(f"[{idx}] ERROR: {e}")
            levels[idx] = 0.0

    best = max(levels, key=levels.get)
    print(f"best device: [{best}] rms={levels[best]:.1f}")
    if levels[best] < 30:
        print("VERDICT: no meaningful audio on ANY candidate device —")
        print("the FT-710 USB audio path itself is silent (AF gain/menu/cable),")
        print("so filter changes cannot be heard regardless of device choice.")
        pa.terminate()
        return

    # 2) does the SH filter affect the captured spectrum?
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()
    send(ser, "AI0")
    time.sleep(0.2)
    ser.reset_input_buffer()
    print("ID ->", query(ser, "ID"), " MD0 ->", query(ser, "MD0"))
    orig = query(ser, "SH0")
    print("SH0 original ->", repr(orig))

    send(ser, f"SH00{WIDE:02d}")
    time.sleep(0.5)
    a = capture(pa, best, 3.0)
    print("SH0 wide check  ->", repr(query(ser, "SH0")))

    send(ser, f"SH00{NARROW:02d}")
    time.sleep(0.5)
    b = capture(pa, best, 3.0)
    print("SH0 narrow check->", repr(query(ser, "SH0")))

    # restore original width
    if orig and len(orig) >= 2:
        send(ser, f"SH00{orig[-2:]}")
        time.sleep(0.2)
    ser.close()
    pa.terminate()

    e_wide = band_frac(a, 1500, 8000)
    e_narrow = band_frac(b, 1500, 8000)
    print(f"rms wide={rms(a):.1f} narrow={rms(b):.1f}")
    print(f"energy >1.5kHz: wide={e_wide:.3f} narrow={e_narrow:.3f} "
          f"ratio={e_narrow / (e_wide + 1e-9):.2f}")
    if e_narrow < 0.7 * e_wide:
        print("VERDICT: filter EFFECT reaches the audio path on this device.")
    else:
        print("VERDICT: filter has NO spectral effect on this audio path —")
        print("either the wrong device was chosen or the USB audio tap is pre-filter.")


if __name__ == "__main__":
    main()
