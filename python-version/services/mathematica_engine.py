"""Local Wolfram Mathematica integration layer.

Uses wolframclient (WolframLanguageSession) as the primary interface.
Falls back to subprocess-based MathKernel calls if wolframclient is unavailable.
All Mathematica communication is local — no cloud dependency.
"""
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from config import MATHEMATICA_KERNEL_PATH

logger = logging.getLogger(__name__)

# Try wolframclient first
_USE_WOLFRAMCLIENT = False
_session = None

try:
    from wolframclient.evaluation import WolframLanguageSession
    from wolframclient.language import wl, wlexpr
    _USE_WOLFRAMCLIENT = True
    logger.info("wolframclient available — will use WolframLanguageSession.")
except ImportError:
    logger.info("wolframclient not installed — will use subprocess fallback.")


def _kernel_path() -> Optional[str]:
    """Return the Mathematica kernel path, or None."""
    if MATHEMATICA_KERNEL_PATH:
        return MATHEMATICA_KERNEL_PATH
    # Try to find on PATH
    path = shutil.which("MathKernel") or shutil.which("WolframKernel")
    return path


def _wolframscript_path() -> Optional[str]:
    """Return the wolframscript path, or None."""
    # Check next to the kernel first
    kernel = _kernel_path()
    if kernel:
        candidate = Path(kernel).parent / "wolframscript.exe"
        if candidate.exists():
            return str(candidate)
    # Try PATH
    return shutil.which("wolframscript")


def _get_session():
    """Lazily start a WolframLanguageSession."""
    global _session
    if _session is None:
        kernel = _kernel_path()
        if kernel:
            _session = WolframLanguageSession(kernel)
        else:
            _session = WolframLanguageSession()  # let wolframclient find it
        _session.start()
        logger.info("Wolfram session started.")
    return _session


def _subprocess_evaluate(expr: str) -> str:
    """Evaluate a Mathematica expression via subprocess using wolframscript."""
    ws = _wolframscript_path()
    if ws:
        cmd = [ws, "-code", expr]
    else:
        kernel = _kernel_path()
        if kernel is None:
            raise RuntimeError(
                "Mathematica kernel not found. Set MATHEMATICA_KERNEL_PATH in config.py "
                "or install wolframclient."
            )
        cmd = [kernel, "-noprompt", "-run", f"Print[{expr}]; Exit[]"]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"Mathematica error: {result.stderr.strip()}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("Mathematica returned empty output.")
    return output


def evaluate(expr: str) -> str:
    """Evaluate a Mathematica expression string and return the result as a string.
    
    Args:
        expr: A valid Wolfram Language expression string.
        
    Returns:
        String representation of the result.
    """
    if _USE_WOLFRAMCLIENT:
        session = _get_session()
        result = session.evaluate(wlexpr(expr))
        return str(result)
    else:
        return _subprocess_evaluate(expr)


def simplify_formula(expr: str) -> str:
    """Simplify a symbolic expression using Mathematica."""
    return evaluate(f"FullSimplify[{expr}]")


def validate_recurrence(
    initial_deposit: float,
    monthly_deposit: float,
    returns: list[float],
    expected_final: float,
    tolerance: float = 1e-6,
) -> dict:
    """Validate the recurrence result using Mathematica.
    
    Builds the recurrence in Wolfram Language and compares with expected_final.
    
    Returns:
        Dict with keys: mathematica_result (float), expected (float),
        difference (float), valid (bool).
    """
    n = len(returns)
    # Build the Wolfram expression for the recurrence
    returns_str = "{" + ", ".join(f"{r}" for r in returns) + "}"
    expr = (
        f"Module[{{x = {initial_deposit}, returns = {returns_str}}}, "
        f"Do[x = (x + {monthly_deposit}) * (1 + returns[[i]]), {{i, 1, {n}}}]; "
        f"N[x, 20]]"
    )
    try:
        result_str = evaluate(expr)
        math_result = float(result_str)
        diff = abs(math_result - expected_final)
        return {
            "mathematica_result": math_result,
            "expected": expected_final,
            "difference": diff,
            "valid": diff < tolerance,
        }
    except Exception as e:
        logger.error("Mathematica validation failed: %s", e)
        return {
            "mathematica_result": None,
            "expected": expected_final,
            "difference": None,
            "valid": False,
            "error": str(e),
        }


def solve_numerically(
    variable: str,
    equation: str,
    initial_guess: float = 0.0,
) -> Optional[float]:
    """Solve a one-variable equation numerically using Mathematica's FindRoot.
    
    Args:
        variable: Variable name in the equation (e.g., "x").
        equation: Equation string in Wolfram Language (e.g., "x^2 - 4 == 0").
        initial_guess: Starting point for FindRoot.
        
    Returns:
        Numerical solution, or None on failure.
    """
    expr = f"FindRoot[{equation}, {{{variable}, {initial_guess}}}]"
    try:
        result_str = evaluate(expr)
        # Result looks like {x -> 2.0}
        # Parse the numerical value
        import re
        match = re.search(r"->?\s*([-\d.eE+]+)", result_str)
        if match:
            return float(match.group(1))
        logger.warning("Could not parse FindRoot result: %s", result_str)
        return None
    except Exception as e:
        logger.error("Mathematica FindRoot failed: %s", e)
        return None


def compute_equivalent_annual_return(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
    target_final: float,
    initial_guess: float = 0.05,
) -> Optional[float]:
    """Solve for equivalent annual return using Mathematica.
    
    Builds the constant-return recurrence equation and solves for the
    annual return r_y where r_m = (1 + r_y)^(1/12) - 1.
    """
    # Build equation: forward_value(A, b, ((1+ry)^(1/12)-1), n) == target
    expr = (
        f"Module[{{ry}}, "
        f"FindRoot["
        f"  Module[{{rm = (1 + ry)^(1/12) - 1, x = {initial_deposit}}}, "
        f"    Do[x = (x + {monthly_deposit}) * (1 + rm), {{i, 1, {num_periods}}}]; "
        f"    x] == {target_final}, "
        f"  {{ry, {initial_guess}}}]]"
    )
    try:
        result_str = evaluate(expr)
        import re
        match = re.search(r"->?\s*([-\d.eE+]+)", result_str)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        logger.error("Mathematica annual return solve failed: %s", e)
        return None


def shutdown():
    """Shut down the Wolfram session if active."""
    global _session
    if _session is not None:
        try:
            _session.terminate()
            logger.info("Wolfram session terminated.")
        except Exception:
            pass
        _session = None
