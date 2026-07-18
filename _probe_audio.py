#!/usr/bin/env python3
"""One-off probe: measure audio levels/spectra on candidate input devices
to identify which one actually carries the FT-710's RX audio."""
import numpy as np
import pyaudio

DEVICES = [3, 4, 5]
RATE = 44100
SECONDS = 2


def capture(pa, idx):
    info = pa.get_device_info_by_index(idx)
    ch = min(2, int(info.get("maxInputChannels", 1)))
    st = pa.open(format=pyaudio.paInt16, channels=ch, rate=RATE,
                 input=True, input_device_index=idx, frames_per_buffer=1024)
    frames = []
    for _ in range(int(RATE / 1024 * SECONDS)):
        frames.append(st.read(1024, exception_on_overflow=False))
    st.stop_stream()
    st.close()
    x = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    return info.get("name", ""), x


def analyze(x):
    rms = float(np.sqrt(np.mean(x ** 2)))
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    n = len(x)
    X = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / RATE)

    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return float(X[m].sum())

    total = band(20, 22050) + 1e-9
    speech = band(300, 3000) / total
    hf = band(3000, 8000) / total
    return rms, peak, speech, hf


def main():
    pa = pyaudio.PyAudio()
    for idx in DEVICES:
        try:
            name, x = capture(pa, idx)
            rms, peak, speech, hf = analyze(x)
            print(f"[{idx}] {name!r:28s} rms={rms:8.1f} peak={peak:6.0f} "
                  f"speech300-3k={speech:.2f} hf3-8k={hf:.2f}")
        except Exception as e:
            print(f"[{idx}] ERROR: {e}")
    pa.terminate()


if __name__ == "__main__":
    main()
