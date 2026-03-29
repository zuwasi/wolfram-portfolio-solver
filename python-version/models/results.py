"""Result dataclasses for investment simulation and solver outputs."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationResult:
    """Result of a forward investment simulation.

    Attributes:
        final_value: Portfolio value at the end of the simulation.
        total_contributions: Sum of initial deposit and all monthly deposits.
        total_growth: final_value - total_contributions.
        annualized_return: CAGR over the simulation period, if computable.
        monthly_values: Portfolio value at each time step (length = num_periods + 1).
        monthly_returns: Monthly return applied at each period.
        dates: Date labels corresponding to monthly_values.
        num_periods: Number of monthly periods simulated.
        deposit_timing: Description of when deposits are applied.
    """

    final_value: float
    total_contributions: float
    total_growth: float
    annualized_return: float | None
    monthly_values: list[float]
    monthly_returns: list[float]
    dates: list[Any]
    num_periods: int
    deposit_timing: str = "beginning of month"


@dataclass
class SolverResult:
    """Result of a reverse-solve operation.

    Attributes:
        value: The solved-for quantity.
        converged: Whether the solver converged within tolerance.
        iterations: Number of iterations performed.
        final_residual: Absolute residual at the solution.
        error_message: Description of failure, or None on success.
    """

    value: float
    converged: bool
    iterations: int
    final_residual: float
    error_message: str | None = None
