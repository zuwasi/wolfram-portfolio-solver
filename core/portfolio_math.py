"""Forward recurrence — Mathematica-only version.

All calculations are performed by the local Wolfram kernel via wolframscript.

Recurrence:
    x_(n+1) = (x_n + b) * (1 + p_n)

Convention:
    - x_0 = initial deposit, present before the first return period.
    - Monthly deposit b is added at the beginning of each month before
      that month's return is applied.
    - The returned list contains [x_0, x_1, ..., x_n] (length = len(returns) + 1).
"""

from __future__ import annotations

from services.mathematica_engine import evaluate, evaluate_float


def forward_simulation(
    initial_deposit: float,
    monthly_deposit: float,
    returns: list[float],
) -> list[float]:
    """Run the forward recurrence in Mathematica and return all intermediate values.

    Args:
        initial_deposit: Starting capital (A = x_0).
        monthly_deposit: Constant deposit added each period (b).
        returns: List of periodic returns [p_0, p_1, ..., p_(n-1)].

    Returns:
        List of portfolio values [x_0, x_1, ..., x_n].
    """
    n = len(returns)
    if n == 0:
        return [initial_deposit]

    returns_str = "{" + ", ".join(f"{r!r}" for r in returns) + "}"
    # Build a Wolfram expression that accumulates all values into a list
    # Use CForm for each value to get C-style scientific notation (e.g. 1.04e6)
    expr = (
        f"Module[{{x = {initial_deposit!r}, ret = {returns_str}, vals}}, "
        f"vals = {{x}}; "
        f"Do[x = (x + {monthly_deposit!r}) * (1 + ret[[i]]); "
        f"AppendTo[vals, x], {{i, 1, {n}}}]; "
        f"StringRiffle[ToString[CForm[#]] & /@ N[vals, 20], \",\"]]"
    )
    raw = evaluate(expr)
    # Result is comma-separated C-style floats
    raw = " ".join(raw.split())  # collapse newlines/whitespace
    parts = [s.strip() for s in raw.split(",")]
    return [float(p) for p in parts]


def forward_simulation_constant_return(
    initial_deposit: float,
    monthly_deposit: float,
    monthly_return: float,
    num_periods: int,
) -> list[float]:
    """Forward recurrence with a constant monthly return, computed in Mathematica."""
    returns = [monthly_return] * num_periods
    return forward_simulation(initial_deposit, monthly_deposit, returns)


def compute_annualized_return(
    monthly_values: list[float],
    initial_deposit: float,
    total_contributions: float,
    num_periods: int,
) -> float:
    """Compute CAGR using Mathematica.

    CAGR = (final / initial)^(12/n) - 1, using total contributions as the
    effective base when monthly deposits are present.
    """
    final = monthly_values[-1]
    if total_contributions <= 0 or num_periods <= 0:
        return 0.0
    expr = f"(({final!r} / {total_contributions!r})^(12/{num_periods}) - 1)"
    return evaluate_float(expr)


def compute_total_contributions(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
) -> float:
    """Total money deposited = A + b * n."""
    return initial_deposit + monthly_deposit * num_periods
