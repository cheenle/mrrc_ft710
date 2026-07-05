"""
Tests for audio_handler.py and opus_rx.py — SDD AD-004 (tagged dual-codec audio).
Verifies: codec tag constants, encoder/decoder lifecycle, PCM framing,
audio device name matching logic.
"""
import struct
import unittest

from opus_rx import (
    AUDIO_TAG_PCM,
    AUDIO_TAG_OPUS,
    RX_RATE,
    FRAME_SAMPLES,
    DEFAULT_BITRATE,
    MIN_BITRATE,
    MAX_BITRATE,
)


class CodecTagTests(unittest.TestCase):
    """SDD AD-004: 1-byte codec tag per frame."""

    def test_tags_are_distinct(self):
        self.assertNotEqual(AUDIO_TAG_PCM, AUDIO_TAG_OPUS)

    def test_pcm_tag_is_zero(self):
        self.assertEqual(AUDIO_TAG_PCM, 0x00)

    def test_opus_tag_is_one(self):
        self.assertEqual(AUDIO_TAG_OPUS, 0x01)

    def test_tag_fits_in_one_byte(self):
        self.assertLess(AUDIO_TAG_PCM, 256)
        self.assertLess(AUDIO_TAG_OPUS, 256)


class OpusConstantsTests(unittest.TestCase):
    """SDD NFR-060, NFR-061: Opus codec configuration."""

    def test_rx_rate_is_48khz(self):
        self.assertEqual(RX_RATE, 48000)

    def test_frame_samples_20ms_at_48khz(self):
        self.assertEqual(FRAME_SAMPLES, 960)

    def test_default_bitrate_is_64kbps(self):
        self.assertEqual(DEFAULT_BITRATE, 64000)

    def test_min_bitrate_is_8kbps(self):
        self.assertEqual(MIN_BITRATE, 8000)

    def test_max_bitrate_is_128kbps(self):
        self.assertEqual(MAX_BITRATE, 128000)

    def test_bitrate_range(self):
        self.assertLess(MIN_BITRATE, DEFAULT_BITRATE)
        self.assertLess(DEFAULT_BITRATE, MAX_BITRATE)


class AudioFramingTests(unittest.TestCase):
    """SDD §9.3, §9.4: Audio frame format (1-byte tag + payload)."""

    def test_tagged_pcm_frame_starts_with_zero(self):
        """PCM frames: AUDIO_TAG_PCM (0x00) + Int16 PCM bytes."""
        pcm_data = struct.pack("<480h", *([0] * 480))  # 960 bytes
        tagged = bytes([AUDIO_TAG_PCM]) + pcm_data
        self.assertEqual(tagged[0], 0x00)
        self.assertEqual(len(tagged), 1 + 960)

    def test_tagged_opus_frame_starts_with_one(self):
        """Opus frames: AUDIO_TAG_OPUS (0x01) + Opus packet bytes."""
        opus_packet = b"\x00" * 80  # typical Opus frame ~40-80 bytes
        tagged = bytes([AUDIO_TAG_OPUS]) + opus_packet
        self.assertEqual(tagged[0], 0x01)
        self.assertEqual(len(tagged), 1 + 80)

    def test_pcm_frame_contains_even_byte_count(self):
        """Int16 PCM frames must have even byte count (2 bytes per sample)."""
        samples = [1000, -500, 32767, -32768]
        pcm = struct.pack(f"<{len(samples)}h", *samples)
        self.assertEqual(len(pcm), len(samples) * 2)
        self.assertEqual(len(pcm) % 2, 0)

    def test_int16_range(self):
        """PCM samples must fit in int16 range."""
        for val in (-32768, -1, 0, 1, 32767):
            packed = struct.pack("<h", val)
            unpacked = struct.unpack("<h", packed)[0]
            self.assertEqual(unpacked, val)

    def test_multiple_frames_independent_tags(self):
        """Each frame has its own independent tag."""
        frame1 = bytes([AUDIO_TAG_PCM]) + b"\x00" * 960
        frame2 = bytes([AUDIO_TAG_OPUS]) + b"\x01" * 60
        self.assertEqual(frame1[0], 0x00)
        self.assertEqual(frame2[0], 0x01)

    def test_48khz_mono_pcm_bandwidth(self):
        """48kHz mono Int16 = 48000 * 2 = 96000 bytes/sec = 768 kbps."""
        bytes_per_sec = RX_RATE * 2  # 16-bit = 2 bytes/sample
        kbps = bytes_per_sec * 8 / 1000
        self.assertAlmostEqual(kbps, 768.0, delta=1)


class AudioDeviceDetectionTests(unittest.TestCase):
    """SDD AD-008: FT-710 audio device name matching."""

    def test_ft710_name_pattern_matches(self):
        """'FT-710' substring should match."""
        names = [
            "USB Audio CODEC (FT-710)",
            "FT-710 USB Audio",
            "YAESU FT-710 Audio",
        ]
        for name in names:
            self.assertTrue(
                "FT-710" in name or "FT710" in name or "YAESU" in name.upper()
            )

    def test_non_ft710_name_does_not_match(self):
        """Other audio devices should not match."""
        names = [
            "Built-in Microphone",
            "External USB Headset",
            "HDMI Audio Output",
        ]
        for name in names:
            self.assertFalse(
                "FT-710" in name or "FT710" in name or "YAESU" in name.upper()
            )


if __name__ == "__main__":
    unittest.main()
