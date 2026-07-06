"""
FT-710 Audio Resampler
======================
Stateless 44.1 kHz ↔ 48 kHz sample-rate conversion using numpy linear
interpolation.  The FT-710 USB audio interface natively runs at 44.1 kHz
but Opus requires 48 kHz (44.1k is not a supported Opus rate).  These
functions bridge the two domains.

Algorithm: numpy.interp (float32, linear).  Chunk sizes are small (<4000
samples) so the overhead is negligible (~µs per call on modern CPUs).

The ratio 48000/44100 = 160/147 ≈ 1.0884.  Conveniently, exactly 882
samples @ 44.1k = 960 samples @ 48k = 20 ms, so nominal frame boundaries
stay perfectly aligned across resampling — no fractional accumulation.
"""

import numpy as np

HW_RATE = 44100       # FT-710 native USB audio rate
OPUS_RATE = 48000     # Opus codec rate (48 kHz is mandatory for Opus)


def resample_pcm(pcm_bytes: bytes, in_rate: int, out_rate: int) -> bytes:
    """Resample Int16 PCM bytes between two sample rates.

    Uses linear interpolation on float32 arrays.  Handles edge cases:
    empty input, single sample, odd byte count (drops trailing byte).

    Args:
        pcm_bytes: Raw Int16 PCM data (little-endian).
        in_rate: Source sample rate in Hz.
        out_rate: Destination sample rate in Hz.

    Returns:
        Resampled Int16 PCM bytes at out_rate.
    """
    if not pcm_bytes or len(pcm_bytes) < 2:
        return b""

    # Drop trailing byte if odd (broken Int16 boundary)
    byte_len = len(pcm_bytes) & ~1
    if byte_len == 0:
        return b""

    pcm_slice = pcm_bytes[:byte_len]
    in_samples = byte_len // 2
    out_samples = max(1, int(in_samples * out_rate / in_rate + 0.5))

    # Convert to float32 for interpolation
    src = np.frombuffer(pcm_slice, dtype=np.int16).astype(np.float32)

    # Time axes (normalised so dt matches each domain)
    t_in = np.arange(in_samples, dtype=np.float32) / in_rate
    t_out = np.arange(out_samples, dtype=np.float32) / out_rate

    interp = np.interp(t_out, t_in, src).astype(np.float32)

    # Clamp and convert back to int16
    out_i16 = np.clip(np.round(interp), -32768, 32767).astype(np.int16)
    return out_i16.tobytes()


def resample_441_to_48(pcm_bytes: bytes) -> bytes:
    """Resample FT-710 native 44.1 kHz PCM → 48 kHz for Opus encoding."""
    return resample_pcm(pcm_bytes, HW_RATE, OPUS_RATE)


def resample_48_to_441(pcm_bytes: bytes) -> bytes:
    """Resample Opus-decoded 48 kHz PCM → 44.1 kHz for FT-710 playback."""
    return resample_pcm(pcm_bytes, OPUS_RATE, HW_RATE)
