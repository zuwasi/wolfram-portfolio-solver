"""Newton-Raphson solver and reverse solving functions.

Provides generic root-finding utilities and specialised functions that solve
for each unknown in the forward recurrence:

    x_(n+1) = (x_n + b) * (1 + p_n)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from models.results import SolverResult
from core.portfolio_math import forward_simulation, forward_simulation_constant_return


# ---------------------------------------------------------------------------
# Generic root-finding
# ---------------------------------------------------------------------------

@dataclass
class NewtonRaphsonResult:
    """Diagnostics returned by the Newton-Raphson solver.

    Attributes:
        value: Approximate root.
        converged: Whether the solver met the tolerance criterion.
        iterations: Number of iterations performed.
        final_residual: |f(x)| at the returned value.
        error_message: Description of failure, or None on success.
    """

    value: float
    converged: bool
    iterations: int
    final_residual: float
    error_message: str | None = None


def newton_raphson(
    f,
    x0: float,
    tol: float,
    max_iter: int,
    df=None,
    h: float = 1e-8,
) -> NewtonRaphsonResult:
    """Find a root of *f* using the Newton-Raphson method.

    Args:
        f: Scalar function whose root is sought.
        x0: Initial guess.
        tol: Convergence tolerance on |f(x)|.
        max_iter: Maximum number of iterations.
        df: Analytic derivative of *f*. If ``None``, a central-difference
            approximation is used: f'(x) ≈ (f(x+h) − f(x−h)) / (2h).
        h: Step size for numerical differentiation.

    Returns:
        A :class:`NewtonRaphsonResult` with full diagnostics.
    """
    x = x0
    for i in range(1, max_iter + 1):
        fx = f(x)
        if abs(fx) < tol:
            return NewtonRaphsonResult(x, True, i, abs(fx))

        if df is not None:
            dfx = df(x)
        else:
            dfx = (f(x + h) - f(x - h)) / (2.0 * h)

        if dfx == 0.0:
            return NewtonRaphsonResult(
                x, False, i, abs(fx),
                "Derivative is zero; cannot continue Newton-Raphson.",
            )

        x = x - fx / dfx

    fx = f(x)
    return NewtonRaphsonResult(
        x, abs(fx) < tol, max_iter, abs(fx),
        None if abs(fx) < tol else "Did not converge within max iterations.",
    )


def bisection_fallback(
    f,
    a: float,
    b: float,
    tol: float,
    max_iter: int,
) -> NewtonRaphsonResult:
    """Find a root of *f* on [a, b] using the bisection method.

    Args:
        f: Continuous scalar function.
        a: Left endpoint of the bracket.
        b: Right endpoint of the bracket.
        tol: Convergence tolerance on |f(mid)|.
        max_iter: Maximum number of iterations.

    Returns:
        A :class:`NewtonRaphsonResult` with full diagnostics.
    """
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return NewtonRaphsonResult(
            (a + b) / 2.0, False, 0, min(abs(fa), abs(fb)),
            "f(a) and f(b) have the same sign; no bracket.",
        )

    mid = (a + b) / 2.0
    for i in range(1, max_iter + 1):
        mid = (a + b) / 2.0
        fmid = f(mid)
        if abs(fmid) < tol or (b - a) / 2.0 < tol:
            return NewtonRaphsonResult(mid, True, i, abs(fmid))
        if fa * fmid < 0:
            b = mid
        else:
            a = mid
            fa = fmid

    fmid = f(mid)
    return NewtonRaphsonResult(
        mid, abs(fmid) < tol, max_iter, abs(fmid),
        None if abs(fmid) < tol else "Bisection did not converge within max iterations.",
    )


# ---------------------------------------------------------------------------
# Reverse-solving helpers
# ---------------------------------------------------------------------------

def _product_of_returns(returns: list[float]) -> float:
    """Compute ∏(1 + p_i) for all returns."""
    prod = 1.0
    for p in returns:
        prod *= (1.0 + p)
    return prod


def solve_initial_deposit(
    monthly_deposit: float,
    returns: list[float],
    target_final: float,
    tol: float,
    max_iter: int,
) -> SolverResult:
    """Solve for the initial deposit A given everything else.

    The recurrence is **linear** in A.  Expanding the recurrence:

        final = A * ∏(1+p_i) + b * Σ_{k=0}^{N-1} ∏_{j=k}^{N-1} (1+p_j)

    So: A = (target_final − contribution_part) / total_product

    Args:
        monthly_deposit: Amount added each month (b).
        returns: List of monthly returns.
        target_final: Desired final portfolio value.
        tol: Not used (closed-form), kept for API consistency.
        max_iter: Not used (closed-form), kept for API consistency.

    Returns:
        A :class:`SolverResult`.
    """
    n = len(returns)
    total_product = _product_of_returns(returns)

    # Contribution part: b * Σ_{k=0}^{N-1} ∏_{j=k}^{N-1} (1+p_j)
    contribution_part = 0.0
    partial_product = 1.0
    # Build products from the end
    partial_products: list[float] = []
    for p in reversed(returns):
        partial_product *= (1.0 + p)
        partial_products.append(partial_product)
    partial_products.reverse()  # partial_products[k] = ∏_{j=k}^{N-1} (1+p_j)

    contribution_part = monthly_deposit * sum(partial_products)

    if total_product == 0.0:
        return SolverResult(
            value=0.0, converged=False, iterations=0,
            final_residual=abs(target_final), error_message="Total product of returns is zero.",
        )

    a = (target_final - contribution_part) / total_product
    residual = abs(forward_simulation(a, monthly_deposit, returns)[-1] - target_final)
    return SolverResult(value=a, converged=True, iterations=1, final_residual=residual)


def solve_monthly_deposit(
    initial_deposit: float,
    returns: list[float],
    target_final: float,
    tol: float,
    max_iter: int,
) -> SolverResult:
    """Solve for the monthly deposit b given everything else.

    The recurrence is **linear** in b.  Expanding:

        final = A * ∏(1+p_i) + b * Σ_{k=0}^{N-1} ∏_{j=k}^{N-1} (1+p_j)

    So: b = (target_final − A * total_product) / sum_of_products

    Args:
        initial_deposit: Lump-sum at time zero (A).
        returns: List of monthly returns.
        target_final: Desired final portfolio value.
        tol: Not used (closed-form), kept for API consistency.
        max_iter: Not used (closed-form), kept for API consistency.

    Returns:
        A :class:`SolverResult`.
    """
    total_product = _product_of_returns(returns)

    partial_product = 1.0
    partial_products: list[float] = []
    for p in reversed(returns):
        partial_product *= (1.0 + p)
        partial_products.append(partial_product)
    partial_products.reverse()

    sum_of_products = sum(partial_products)
    if sum_of_products == 0.0:
        return SolverResult(
            value=0.0, converged=False, iterations=0,
            final_residual=abs(target_final),
            error_message="Sum of return products is zero; cannot solve for monthly deposit.",
        )

    b = (target_final - initial_deposit * total_product) / sum_of_products
    residual = abs(forward_simulation(initial_deposit, b, returns)[-1] - target_final)
    return SolverResult(value=b, converged=True, iterations=1, final_residual=residual)


def solve_monthly_return(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
    target_final: float,
    tol: float,
    max_iter: int,
    initial_guess: float = 0.005,
) -> SolverResult:
    """Solve for the constant monthly return r.

    This is **nonlinear** in r and is solved with Newton-Raphson.

    f(r) = forward_value(A, b, r, N) − target = 0

    Args:
        initial_deposit: Lump-sum at time zero (A).
        monthly_deposit: Amount added each month (b).
        num_periods: Number of monthly periods (N).
        target_final: Desired final portfolio value.
        tol: Convergence tolerance.
        max_iter: Maximum iterations.
        initial_guess: Starting guess for the monthly return.

    Returns:
        A :class:`SolverResult`.
    """
    def f(r: float) -> float:
        vals = forward_simulation_constant_return(
            initial_deposit, monthly_deposit, r, num_periods,
        )
        return vals[-1] - target_final

    nr = newton_raphson(f, initial_guess, tol, max_iter)
    return SolverResult(
        value=nr.value,
        converged=nr.converged,
        iterations=nr.iterations,
        final_residual=nr.final_residual,
        error_message=nr.error_message,
    )


def solve_annual_return(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
    target_final: float,
    tol: float,
    max_iter: int,
    initial_guess: float = 0.05,
) -> SolverResult:
    """Solve for the constant annual return r_y.

    Converts between annual and monthly via r_m = (1 + r_y)^(1/12) − 1 and
    solves the nonlinear equation with Newton-Raphson.

    Args:
        initial_deposit: Lump-sum at time zero (A).
        monthly_deposit: Amount added each month (b).
        num_periods: Number of monthly periods (N).
        target_final: Desired final portfolio value.
        tol: Convergence tolerance.
        max_iter: Maximum iterations.
        initial_guess: Starting guess for the annual return.

    Returns:
        A :class:`SolverResult` whose ``value`` is the annual return.
    """
    def f(r_y: float) -> float:
        if r_y <= -1.0:
            return float("inf")
        r_m = (1.0 + r_y) ** (1.0 / 12.0) - 1.0
        vals = forward_simulation_constant_return(
            initial_deposit, monthly_deposit, r_m, num_periods,
        )
        return vals[-1] - target_final

    nr = newton_raphson(f, initial_guess, tol, max_iter)
    return SolverResult(
        value=nr.value,
        converged=nr.converged,
        iterations=nr.iterations,
        final_residual=nr.final_residual,
        error_message=nr.error_message,
    )


def solve_final_amount(
    initial_deposit: float,
    monthly_deposit: float,
    returns: list[float],
) -> SolverResult:
    """Trivially run the forward simulation and return the final value.

    Args:
        initial_deposit: Lump-sum at time zero (A).
        monthly_deposit: Amount added each month (b).
        returns: List of monthly returns.

    Returns:
        A :class:`SolverResult` with the final portfolio value.
    """
    vals = forward_simulation(initial_deposit, monthly_deposit, returns)
    final = vals[-1]
    return SolverResult(
        value=final, converged=True, iterations=0, final_residual=0.0,
    )
