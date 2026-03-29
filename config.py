"""Configuration module — Mathematica-only version."""

from pathlib import Path
import shutil


def _detect_wolframscript() -> str | None:
    """Auto-detect wolframscript on Windows."""
    # Check common Wolfram Research install paths
    root = Path(r"C:\Program Files\Wolfram Research")
    if root.exists():
        for product in ("Mathematica", "Wolfram"):
            base = root / product
            if not base.exists():
                continue
            version_dirs = sorted(
                (d for d in base.iterdir() if d.is_dir()),
                key=lambda d: d.name,
                reverse=True,
            )
            for vdir in version_dirs:
                ws = vdir / "wolframscript.exe"
                if ws.exists():
                    return str(ws)
    # Try PATH
    return shutil.which("wolframscript")


WOLFRAMSCRIPT_PATH: str | None = _detect_wolframscript()

DEFAULT_SOLVER_TOLERANCE: float = 1e-10
DEFAULT_MAX_ITERATIONS: int = 1000
DEFAULT_DATA_PROVIDER: str = "yfinance"
DEFAULT_CHART_DPI: int = 100
DEFAULT_CHART_FIGSIZE: tuple[int, int] = (10, 6)
