"""Wolfram Mathematica engine — ALL computation goes through wolframscript.

This is the Mathematica-only version. Every mathematical operation
(forward simulation, reverse solving, validation) is performed by
the local Wolfram kernel via wolframscript.
"""

import logging
import subprocess
from typing import Optional

from config import WOLFRAMSCRIPT_PATH

logger = logging.getLogger(__name__)


def _ws() -> str:
    """Return wolframscript path or raise."""
    if WOLFRAMSCRIPT_PATH is None:
        raise RuntimeError(
            "wolframscript not found. Install Wolfram Mathematica and ensure "
            "wolframscript.exe is accessible, or set WOLFRAMSCRIPT_PATH in config.py."
        )
    return WOLFRAMSCRIPT_PATH


def evaluate(expr: str, timeout: int = 120) -> str:
    """Evaluate a Wolfram Language expression and return the result as a string."""
    result = subprocess.run(
        [_ws(), "-code", expr],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Mathematica error: {result.stderr.strip()}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"Mathematica returned empty output for: {expr}")
    return output


def evaluate_float(expr: str) -> float:
    """Evaluate an expression and return the result as a float."""
    raw = evaluate(f"N[{expr}, 20]")
    # Handle Mathematica scientific notation like 1.23*^-4
    raw = raw.replace("*^", "e")
    return float(raw)
