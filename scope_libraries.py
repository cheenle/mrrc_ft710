"""
FTDI library discovery for FT-710 scope support.

The project is intended to run standalone. Prefer libraries copied into this
repository, while still allowing explicit environment overrides.
"""
from pathlib import Path
from typing import Optional
import os


SCRIPT_DIR = Path(__file__).parent


def _libs_in_dir(directory: Path) -> tuple[Optional[Path], Optional[Path]]:
    # Try the original library first (known to work better with FT4222 SPI)
    # Versioned library is available as fallback for different devices
    for name_pair in [
        ("libft4222.dylib", "libftd2xx.dylib"),           # original (SPI init works)
        ("libft4222.dylib", "libftd2xx.1.4.35.dylib"),    # newer version
    ]:
        ft4222 = directory / name_pair[0]
        ftd2xx = directory / name_pair[1]
        if ft4222.exists() and ftd2xx.exists():
            return ft4222, ftd2xx
    return None, None


def find_ftdi_libraries() -> tuple[Optional[Path], Optional[Path]]:
    """Return FT4222 and FTD2XX dylib paths, or (None, None)."""
    explicit_ft4222 = os.environ.get("FT710_FT4222_DYLIB")
    explicit_ftd2xx = os.environ.get("FT710_FTD2XX_DYLIB")
    if explicit_ft4222 and explicit_ftd2xx:
        ft4222 = Path(explicit_ft4222)
        ftd2xx = Path(explicit_ftd2xx)
        if ft4222.exists() and ftd2xx.exists():
            return ft4222, ftd2xx

    candidate_dirs = []
    if os.environ.get("FT710_FTDI_LIB_DIR"):
        candidate_dirs.append(Path(os.environ["FT710_FTDI_LIB_DIR"]))
    candidate_dirs.extend([
        SCRIPT_DIR / "lib",
        SCRIPT_DIR / "vendor" / "ftdi",
    ])

    for directory in candidate_dirs:
        ft4222, ftd2xx = _libs_in_dir(directory)
        if ft4222 and ftd2xx:
            return ft4222, ftd2xx
    return None, None


def require_ftdi_libraries() -> tuple[Path, Path]:
    ft4222, ftd2xx = find_ftdi_libraries()
    if ft4222 is None or ftd2xx is None:
        raise FileNotFoundError(
            "FTDI libraries not found. Put libft4222.dylib and libftd2xx.dylib "
            "in ./lib or ./vendor/ftdi, or set FT710_FTDI_LIB_DIR."
        )
    return ft4222, ftd2xx


def get_ft4222_clock_divider() -> int:
    """Return FT4222 SPI clock divider enum value.

    wfview uses CLK_DIV_64 (enum value 7) with SYS_CLK_24 for FT-710 scope.
    Hardware experiments can override this without code edits.
    """
    raw = os.environ.get("FT710_FT4222_CLK_DIV", "5")  # CLK_DIV_16 for ~15-20fps
    try:
        value = int(raw)
    except ValueError:
        return 5
    return value if 1 <= value <= 9 else 5
