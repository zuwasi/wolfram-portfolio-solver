"""Forward recurrence implementation for investment portfolio simulation.

Time convention
---------------
- x_0 = initial_deposit (present before the first return period).
- At each period n, the monthly deposit b is added at the **beginning** of the
  month, then the return for that month is applied:

      x_(n+1) = (x_n + b) * (1 + p_n)

- The returns list [p_0, p_1, ..., p_(N-1)] has length N.
- The result list [x_0, x_1, ..., x_N] has length N + 1.
"""

import math


def forward_simulation(
    initial_deposit: float,
    monthly_deposit: float,
    returns: list[float],
) -> list[float]:
    """Run the forward recurrence with a sequence of monthly returns.

    Args:
        initial_deposit: Lump-sum amount at time zero (x_0).
        monthly_deposit: Amount added at the beginning of each month.
        returns: List of monthly returns [p_0, p_1, ...].

    Returns:
        Portfolio values [x_0, x_1, ..., x_N] where N = len(returns).
    """
    values = [initial_deposit]
    x = initial_deposit
    for p in returns:
        x = (x + monthly_deposit) * (1.0 + p)
        values.append(x)
    return values


def forward_simulation_constant_return(
    initial_deposit: float,
    monthly_deposit: float,
    monthly_return: float,
    num_periods: int,
) -> list[float]:
    """Run the forward recurrence with a constant monthly return.

    Applies the same recurrence as :func:`forward_simulation` but uses a
    single constant return ``monthly_return`` for every period.

    Args:
        initial_deposit: Lump-sum amount at time zero (x_0).
        monthly_deposit: Amount added at the beginning of each month.
        monthly_return: Constant monthly return applied each period.
        num_periods: Number of monthly periods to simulate.

    Returns:
        Portfolio values [x_0, x_1, ..., x_N] where N = num_periods.
    """
    returns = [monthly_return] * num_periods
    return forward_simulation(initial_deposit, monthly_deposit, returns)


def compute_annualized_return(
    monthly_values: list[float],
    initial_deposit: float,
    total_contributions: float,
    num_periods: int,
) -> float:
    """Compute the Compound Annual Growth Rate (CAGR) from actual growth.

    CAGR = (final_value / total_contributions)^(12 / num_periods) - 1

    Args:
        monthly_values: Portfolio values over time (last element is final value).
        initial_deposit: Lump-sum amount at time zero.
        total_contributions: Sum of initial deposit and all monthly deposits.
        num_periods: Number of monthly periods.

    Returns:
        Annualized (CAGR) return as a decimal.

    Raises:
        ValueError: If total_contributions is zero or num_periods is zero.
    """
    if num_periods == 0:
        raise ValueError("num_periods must be > 0 to compute annualized return")
    if total_contributions <= 0:
        raise ValueError("total_contributions must be > 0 to compute annualized return")

    final_value = monthly_values[-1]
    years = num_periods / 12.0
    return (final_value / total_contributions) ** (1.0 / years) - 1.0


def compute_total_contributions(
    initial_deposit: float,
    monthly_deposit: float,
    num_periods: int,
) -> float:
    """Compute total money contributed over the simulation.

    Total = initial_deposit + monthly_deposit * num_periods

    Args:
        initial_deposit: Lump-sum amount at time zero.
        monthly_deposit: Amount added each month.
        num_periods: Number of monthly periods.

    Returns:
        Total contributions.
    """
    return initial_deposit + monthly_deposit * num_periods
