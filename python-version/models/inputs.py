"""Input dataclasses and enums for investment simulation."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class SolverMode(Enum):
    """Enumeration of available solver modes."""

    FORWARD = "forward"
    SOLVE_INITIAL_DEPOSIT = "solve_initial_deposit"
    SOLVE_MONTHLY_DEPOSIT = "solve_monthly_deposit"
    SOLVE_MONTHLY_RETURN = "solve_monthly_return"
    SOLVE_ANNUAL_RETURN = "solve_annual_return"
    SOLVE_FINAL_AMOUNT = "solve_final_amount"


@dataclass
class SimulationInputs:
    """Inputs for a forward investment simulation.

    Attributes:
        ticker: Stock ticker symbol (e.g. "SPY").
        start_date: Start date for historical data retrieval.
        end_date: End date for historical data retrieval.
        initial_deposit: Lump-sum amount deposited at time zero.
        monthly_deposit: Amount added at the beginning of each month.
        use_historical_returns: If True, use historical returns from ticker data;
            otherwise use constant_monthly_return.
        constant_monthly_return: Fixed monthly return when not using historical data.
        num_periods: Number of monthly periods for constant-return simulation.
    """

    ticker: str
    start_date: date
    end_date: date
    initial_deposit: float
    monthly_deposit: float
    use_historical_returns: bool
    constant_monthly_return: float | None = None
    num_periods: int | None = None


@dataclass
class SolverInputs:
    """Inputs for the reverse solver.

    Attributes:
        mode: Which variable to solve for.
        target_final_value: Desired final portfolio value.
        initial_guess: Starting guess for Newton-Raphson iterations.
        tolerance: Convergence tolerance for the solver.
        max_iterations: Maximum number of solver iterations.
    """

    mode: SolverMode
    target_final_value: float | None = None
    initial_guess: float | None = None
    tolerance: float = 1e-10
    max_iterations: int = 1000
