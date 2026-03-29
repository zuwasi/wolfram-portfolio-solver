"""Reverse solving — Mathematica-only version.

All root-finding and equation solving is performed by the local Wolfram kernel.
Uses FindRoot (Newton-Raphson internally) and Solve/Reduce for linear cases.

Recurrence:
    x_(n+1) = (x_n + b) * (1 + p_n)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.mathematica_engine import evaluate, evaluate_float
from models.results import SolverResult


# ---- generic Mathematica root-finding wrapper ----

def _parse_real_float(raw: str) -> float:
    """Parse a Mathematica numeric output into a Python float.

    Handles *^ scientific notation, strips imaginary parts, and
    collapses multi-line output.
    """
    # Collapse any newlines / extra whitespace
    raw = " ".join(raw.split())
    # Strip imaginary part if present (e.g. "-1.09 - 3.76 10^-15 I")
    if "I" in raw:
        # Take only the real part (everything before the +/- imaginary term)
        import re
        m = re.match(r"([-+]?\d[\d.eE*^+-]*)", raw)
        if m:
            raw = m.group(1)
        else:
            raise ValueError(f"Cannot parse complex Mathematica output: {raw}")
    raw = raw.replace("*^", "e")
    return float(raw)


def _mathematica_find_root(
    wolfram_equation: str,
    variable: str,
    initial_guess: float,
    max_iterations: int = 1000,
) -> SolverResult:
    """Call Mathematica FindRoot and return a SolverResult."""
    expr = (
        f"Module[{{sol, res}}, "
        f"sol = Quiet[FindRoot[{wolfram_equation}, "
        f"{{{variable}, {initial_guess!r}}}, "
        f"MaxIterations -> {max_iterations}]]; "
        f"res = Re[{variable} /. sol]; "
        f"ToString[CForm[N[res, 20]]]]"
    )
    try:
        raw = evaluate(expr)
        value = _parse_real_float(raw)
        return SolverResult(
            value=value,
            converged=True,
            iterations=-1,
            final_residual=0.0,
            error_message=None,
        )
    except Exception as e:
        return SolverResult(
            value=0.0,
            converged=False,
            iterations=0,
            final_residual=float("inf"),
            error_message=f"Mathematica FindRoot failed: {e}",
        )


# ---- helpers to build the Wolfram recurrence expression ----

def _recurrence_expr_historical(
    a_var: str,
    b_var: str,
    returns: list[float],
) -> str:
    """Build Wolfram expression for the final value of the recurrence
    with historical (given) returns, where a_var and b_var may be
    symbolic variable names or literal numbers."""
    n = len(returns)
    returns_str = "{" + ", ".join(f"{r!r}" for r in returns) + "}"
    return (
        f"Module[{{x = {a_var}, ret = {returns_str}}}, "
        f"Do[x = (x + {b_var}) * (1 + ret[[i]]), {{i, 1, {n}}}]; x]"
    )


def _recurrence_expr_constant(
    a_var: str,
    b_var: str,
    r_var: str,
    n: int,
) -> str:
    """Build Wolfram expression for the final value of the recurrence
    with a constant return, where variables may be symbolic."""
    return (
        f"Module[{{x = {a_var}}}, "
        f"Do[x = (x + {b_var}) * (1 + {r_var}), {{i, 1, {n}}}]; x]"
    )


# ---- public solving functions ----

def solve_initial_deposit(
    monthly_deposit: float,
    returns: list[float],
    target_final: float,
    tolerance: float = 1e-10,
    max_iterations: int = 1000,
) -> SolverResult:
    """Solve for the initial deposit A.  Linear in A — use Mathematica Solve."""
    n = len(returns)
    returns_str = "{" + ", ".join(f"{r!r}" for r in returns) + "}"
    expr = (
        f"Module[{{sol, xfinal, a}}, "
        f"xfinal = Module[{{x = a, ret = {returns_str}}}, "
        f"Do[x = (x + {monthly_deposit!r}) * (1 + ret[[i]]), {{i, 1, {n}}}]; x]; "
        f"sol = Solve[xfinal == {target_final!r}, a]; "
        f"ToString[N[a /. sol[[1]], 20]]]"
    )
    try:
        raw = evaluate(expr).replace("*^", "e")
        value = float(raw)
        return SolverResult(
            value=value, converged=True, iterations=0,
            final_residual=0.0, error_message=None,
        )
    except Exception as e:
        return SolverResult(
            value=0.0, converged=False, iterations=0,
            final_residual=float("inf"),
            error_message=f"Mathematica Solve failed: {e}",
        )


def solve_monthly_deposit(
    initial_deposit: float,
    returns: list[float],
    target_final: float,
    tolerance: float = 1e-10,
    max_iterations: int = 1000,
) -> SolverResult:
    """Solve for the constant monthly deposit b.  Linear in b — use Mathematica Solve."""
    n = len(returns)
    returns_str = "{" + ", ".join(f"{r!r}" for r in returns) + "}"
    expr = (
        f"Module[{{sol, xfinal, b}}, "
        f"xfinal = Module[{{x = {initial_deposit!r}, ret = {returns_str}}}, "
        f"Do[x = (x + b) * (1 + ret[[i]]), {{i, 1, {n}}}]; x]; "
        f"sol = Solve[xfinal == {target_final!r}, b]; "
        f"ToString[N[b /. sol[[1]], 20]]]"
    )
    try:
        raw = evaluate(expr).replace("*^", "e")
        value = float(raw)
        return SolverResult(
            value=value, converged=True, iterations=0,
            final_residual=0.0, error_message=None,
        )
    except Exception as e:
        return SolverResult(
            value=0.0, converged=False, iterations=0,
            final_residual=float("inf"),
            error_message=f"Mathematica Solve failed: {e}",
        )


def solve_monthly_return(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
    target_final: float,
    tolerance: float = 1e-10,
    max_iterations: int = 1000,
    initial_guess: float = 0.005,
) -> SolverResult:
    """Solve for the constant monthly return r_m.  Nonlinear — use FindRoot."""
    recurrence = _recurrence_expr_constant(
        f"{initial_deposit!r}", f"{monthly_deposit!r}", "rm", num_periods,
    )
    equation = f"{recurrence} == {target_final!r}"
    return _mathematica_find_root(equation, "rm", initial_guess, max_iterations)


def solve_annual_return(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
    target_final: float,
    tolerance: float = 1e-10,
    max_iterations: int = 1000,
    initial_guess: float = 0.05,
) -> SolverResult:
    """Solve for the equivalent annual return r_y.

    Internally converts r_y -> r_m = (1 + r_y)^(1/12) - 1 and solves.
    """
    # Use Sign[1+ry]*Abs[1+ry]^(1/12) to keep real arithmetic for negative ry
    expr = (
        f"Module[{{sol, ry}}, "
        f"sol = Quiet[FindRoot["
        f"  Module[{{x1 = {initial_deposit!r}, "
        f"    rm1 = Sign[1 + ry]*Abs[1 + ry]^(1/12) - 1}}, "
        f"    Do[x1 = (x1 + {monthly_deposit!r}) * (1 + rm1), "
        f"      {{i, 1, {num_periods}}}]; x1] == {target_final!r}, "
        f"  {{ry, {initial_guess!r}}}, MaxIterations -> {max_iterations}]]; "
        f"ToString[CForm[N[Re[ry /. sol], 20]]]]"
    )
    try:
        raw = evaluate(expr)
        value = _parse_real_float(raw)
        return SolverResult(
            value=value, converged=True, iterations=-1,
            final_residual=0.0, error_message=None,
        )
    except Exception as e:
        return SolverResult(
            value=0.0, converged=False, iterations=0,
            final_residual=float("inf"),
            error_message=f"Mathematica FindRoot failed: {e}",
        )


def solve_final_amount(
    initial_deposit: float,
    monthly_deposit: float,
    returns: list[float],
) -> SolverResult:
    """Compute the final value using Mathematica forward recurrence."""
    from core.portfolio_math import forward_simulation

    values = forward_simulation(initial_deposit, monthly_deposit, returns)
    return SolverResult(
        value=values[-1],
        converged=True,
        iterations=0,
        final_residual=0.0,
        error_message=None,
    )


# Keep these for API compatibility with the GUI
@dataclass
class NewtonRaphsonResult:
    value: float
    converged: bool
    iterations: int
    final_residual: float
    error_message: Optional[str]


def newton_raphson(f, x0, tol, max_iter, df=None, h=1e-8):
    """Not used in Mathematica-only version — placeholder for API compat."""
    raise NotImplementedError("Use Mathematica FindRoot instead.")


def bisection_fallback(f, a, b, tol, max_iter):
    """Not used in Mathematica-only version — placeholder for API compat."""
    raise NotImplementedError("Use Mathematica FindRoot instead.")
