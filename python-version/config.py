"""Configuration module for the investment simulation package."""

from pathlib import Path


def _detect_mathematica_kernel() -> str | None:
    """Auto-detect the Mathematica kernel path on Windows.

    Checks common installation directories for various Mathematica versions
    in descending version order.

    Returns:
        The path to MathKernel.exe if found, otherwise None.
    """
    root = Path(r"C:\Program Files\Wolfram Research")
    if not root.exists():
        return None

    # Check both "Mathematica" and "Wolfram" product folders
    for product in ("Mathematica", "Wolfram"):
        base = root / product
        if not base.exists():
            continue
        # Sort version directories in descending order to prefer the latest
        version_dirs = sorted(
            (d for d in base.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,
        )
        for version_dir in version_dirs:
            kernel = version_dir / "MathKernel.exe"
            if kernel.exists():
                return str(kernel)
    return None


MATHEMATICA_KERNEL_PATH: str | None = _detect_mathematica_kernel()

DEFAULT_SOLVER_TOLERANCE: float = 1e-10
DEFAULT_MAX_ITERATIONS: int = 1000
DEFAULT_DATA_PROVIDER: str = "yfinance"
DEFAULT_CHART_DPI: int = 100
DEFAULT_CHART_FIGSIZE: tuple[int, int] = (10, 6)
