"""
FT-710 Radio State
==================
Thread-safe (asyncio-safe) container for all FT-710 state with
change tracking.  Only dirty (changed) fields are broadcast to clients.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from config import (
    MODE_NUM_TO_NAME, MODE_DISPLAY_NAMES, PREAMP_LABELS, ATTENUATOR_LABELS,
    get_band_for_frequency, get_filter_widths_for_mode, get_filter_hz,
    raw_to_dbm, raw_to_s_unit,
)


@dataclass
class RadioState:
    """Mutable container for all FT-710 state.

    Fields are updated by the poll scheduler and by user commands.
    Change tracking via _dirty_fields enables efficient partial broadcasts.
    """

    # ── Core VFO State ────────────────────────────────────────────
    vfo_a_freq: int = 14_200_000       # Hz
    vfo_b_freq: int = 7_050_000        # Hz
    active_vfo: str = "A"              # "A" or "B"
    mode: int = 1                      # Yaesu mode register (1=LSB, 2=USB, ...)
    tx_status: int = 0                 # 0=RX, 1=TX, 2=TUNE

    # ── Meter Readings (raw 0-255 from radio) ─────────────────────
    s_meter: int = 0                   # SM0;
    comp_meter: int = 0                # RM3; compressor meter
    alc_meter: int = 0                 # RM4; ALC meter
    power_meter: int = 0               # RM5; power meter
    swr_meter: int = 0                 # RM6; SWR meter
    id_meter: int = 0                  # RM7; drain current (Id)
    vd_meter: int = 0                  # RM8; drain voltage (Vd)

    # ── Radio Settings ────────────────────────────────────────────
    af_gain: int = 128                 # AG; 0-255
    rf_gain: int = 255                 # RG; 0-255
    rf_power: int = 100                # PC; 5-100
    filter_width: int = 5              # SH0; filter index
    preamp: int = 0                    # PA0; 0=OFF, 1=AMP1, 2=AMP2
    attenuator: int = 0                # RA0; 0=OFF, 1=6dB, 2=12dB, 3=18dB
    noise_blanker: bool = False        # NB0;
    noise_reduction: bool = False      # NR0;
    auto_notch: bool = False           # BC;
    compressor: bool = False           # PR;
    compressor_level: int = 50         # PL; 1-100
    nr_level: int = 8                  # RL; 1-15 (although we don't poll this)
    nb_level: int = 5                  # NL; 0-10 (although we don't poll this)
    tuner_status: int = 0              # AC; 0=OFF, 1=ON, 2=Tuning
    power_on: bool = True              # PS;
    squelch: int = 0                   # SQ0; 0-100
    mic_gain: int = 50                 # MG; 0-100
    split: bool = False                # ST;
    vox: bool = False                  # VX;
    break_in: bool = False             # BI;

    # ── Scope State ───────────────────────────────────────────────
    scope_span: int = 6                # SS05; 6=100 kHz
    scope_speed: int = 2               # SS00;
    scope_mode: int = 0                # SS06;
    scope_start_freq: int = 0          # Hz, from scope frame metadata when available

    # ── Connection State ──────────────────────────────────────────
    serial_connected: bool = False
    last_update: float = 0.0

    # ── Change Tracking ───────────────────────────────────────────
    _dirty_fields: set[str] = field(default_factory=set, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    # ── Derived Properties ────────────────────────────────────────

    @property
    def active_freq(self) -> int:
        """Current active VFO frequency in Hz."""
        return self.vfo_a_freq if self.active_vfo == "A" else self.vfo_b_freq

    @property
    def mode_name(self) -> str:
        """Human-readable mode name."""
        return MODE_NUM_TO_NAME.get(self.mode, f"M{self.mode:X}")

    @property
    def mode_display(self) -> str:
        """Display-friendly mode name."""
        raw = self.mode_name
        return MODE_DISPLAY_NAMES.get(raw, raw)

    @property
    def band_name(self) -> str:
        """Current band name (e.g. '20m')."""
        band = get_band_for_frequency(self.active_freq)
        return band["name"] if band else "GEN"

    @property
    def s_meter_dbm(self) -> float:
        """S-meter reading in dBm."""
        return raw_to_dbm(self.s_meter)

    @property
    def s_unit(self) -> str:
        """S-meter reading as S-unit string."""
        return raw_to_s_unit(self.s_meter)

    @property
    def filter_hz(self) -> Optional[int]:
        """Current filter width in Hz."""
        return get_filter_hz(self.mode_name, self.filter_width)

    @property
    def preamp_label(self) -> str:
        return PREAMP_LABELS.get(self.preamp, str(self.preamp))

    @property
    def attenuator_label(self) -> str:
        return ATTENUATOR_LABELS.get(self.attenuator, str(self.attenuator))

    @property
    def is_transmitting(self) -> bool:
        return self.tx_status > 0

    # ── State Mutation ────────────────────────────────────────────

    def update(self, **kwargs) -> set[str]:
        """Update one or more fields.  Returns the set of fields that
        actually changed value (may be smaller than the input set)."""
        changed = set()
        for field, new_value in kwargs.items():
            if not hasattr(self, field):
                continue
            old_value = getattr(self, field)
            if old_value != new_value:
                setattr(self, field, new_value)
                changed.add(field)
        if changed:
            self._dirty_fields.update(changed)
            self.last_update = time.time()
        return changed

    def mark_dirty(self, *fields: str):
        """Explicitly mark fields as dirty (for broadcast)."""
        self._dirty_fields.update(fields)

    def get_and_clear_dirty(self) -> set[str]:
        """Atomically get changed fields and reset the dirty set."""
        dirty = self._dirty_fields.copy()
        self._dirty_fields.clear()
        return dirty

    # ── Serialization ─────────────────────────────────────────────

    def to_dict(self, include_derived: bool = True) -> dict:
        """Convert state to a JSON-serializable dict.

        Args:
            include_derived: If True, include computed properties
                            (mode_name, s_unit, band, etc.).
        """
        d = {
            # Core
            "vfo_a_freq": self.vfo_a_freq,
            "vfo_b_freq": self.vfo_b_freq,
            "active_vfo": self.active_vfo,
            "active_freq": self.active_freq,
            "mode": self.mode,
            "tx_status": self.tx_status,
            # Meters
            "s_meter": self.s_meter,
            "comp_meter": self.comp_meter,
            "alc_meter": self.alc_meter,
            "power_meter": self.power_meter,
            "swr_meter": self.swr_meter,
            "id_meter": self.id_meter,
            "vd_meter": self.vd_meter,
            # Settings
            "af_gain": self.af_gain,
            "rf_gain": self.rf_gain,
            "rf_power": self.rf_power,
            "filter_width": self.filter_width,
            "preamp": self.preamp,
            "attenuator": self.attenuator,
            "noise_blanker": self.noise_blanker,
            "noise_reduction": self.noise_reduction,
            "auto_notch": self.auto_notch,
            "compressor": self.compressor,
            "compressor_level": self.compressor_level,
            "nr_level": self.nr_level,
            "nb_level": self.nb_level,
            "tuner_status": self.tuner_status,
            "power_on": self.power_on,
            "squelch": self.squelch,
            "mic_gain": self.mic_gain,
            "split": self.split,
            "vox": self.vox,
            "break_in": self.break_in,
            # Scope
            "scope_span": self.scope_span,
            "scope_speed": self.scope_speed,
            "scope_mode": self.scope_mode,
            "scope_start_freq": self.scope_start_freq,
            # Connection
            "serial_connected": self.serial_connected,
            "last_update": self.last_update,
        }
        if include_derived:
            d.update({
                "mode_name": self.mode_name,
                "mode_display": self.mode_display,
                "band_name": self.band_name,
                "s_meter_dbm": self.s_meter_dbm,
                "s_unit": self.s_unit,
                "filter_hz": self.filter_hz,
                "preamp_label": self.preamp_label,
                "attenuator_label": self.attenuator_label,
                "is_transmitting": self.is_transmitting,
            })
        return d

    def to_dirty_dict(self, fields: set[str]) -> dict:
        """Return a dict with only the given fields.

        If derived fields are requested, those are also resolved.
        """
        full = self.to_dict(include_derived=True)
        return {f: full[f] for f in fields if f in full}

    @classmethod
    def from_sync_result(cls, sync_data: dict) -> "RadioState":
        """Create a RadioState from the raw sync response dict
        returned by CatController.initial_state_sync()."""
        state = cls()
        _parsers = {
            "vfo_a_freq": lambda r: int(r[2:]) if len(r) > 2 else 0,
            "vfo_b_freq": lambda r: int(r[2:]) if len(r) > 2 else 0,
            "mode": lambda r: int(r[3:], 16) if len(r) >= 4 else 1,
            "tx_status": lambda r: int(r[2:]) if len(r) > 2 else 0,
            "s_meter": lambda r: int(r[3:]) if len(r) > 3 else 0,
            "filter_width": lambda r: int(r[3:]) if len(r) > 3 else 1,
            "af_gain_raw": lambda r: int(r[2:]) if len(r) > 2 else 128,
            "rf_power": lambda r: int(r[2:]) if len(r) > 2 else 100,
            "preamp": lambda r: int(r[3:]) if len(r) > 3 else 0,
            "attenuator": lambda r: int(r[3:]) if len(r) > 3 else 0,
            "noise_blanker": lambda r: r.endswith("1"),
            "noise_reduction": lambda r: r.endswith("1"),
            "auto_notch": lambda r: r.endswith("1"),
            "tuner_status": lambda r: int(r[2:]) if len(r) > 2 else 0,
            "power_on": lambda r: r.endswith("1"),
        }

        for field, raw in sync_data.items():
            if field in _parsers and raw:
                try:
                    value = _parsers[field](raw)
                    # Map field names
                    if field == "af_gain_raw":
                        state.af_gain = value
                    else:
                        if hasattr(state, field):
                            setattr(state, field, value)
                except (ValueError, IndexError):
                    pass
        return state
