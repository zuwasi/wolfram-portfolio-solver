"""Monthly return extraction and transformations."""

from datetime import date

import pandas as pd


def compute_monthly_returns(prices: pd.DataFrame) -> list[tuple[date, float]]:
    """Extract monthly returns from a price DataFrame.

    Args:
        prices: DataFrame with a DatetimeIndex and an ``'Adj Close'`` or
            ``'Close'`` column containing daily prices.

    Returns:
        A list of ``(date, return)`` tuples where each return is
        ``price_n / price_(n-1) − 1``, resampled to the last business day
        of each month.

    Raises:
        KeyError: If neither ``'Adj Close'`` nor ``'Close'`` is found.
    """
    if "Adj Close" in prices.columns:
        col = "Adj Close"
    elif "Close" in prices.columns:
        col = "Close"
    else:
        raise KeyError("DataFrame must contain an 'Adj Close' or 'Close' column.")

    series = prices[col]

    # Resample to last business day of each month
    monthly_prices = series.resample("BME").last().dropna()

    # Compute percentage change (p_n = price_n / price_(n-1) - 1)
    monthly_returns = monthly_prices.pct_change().dropna()

    return [
        (idx.date() if hasattr(idx, "date") else idx, float(ret))
        for idx, ret in monthly_returns.items()
    ]


def annualized_return_from_monthly(monthly_return: float) -> float:
    """Convert a monthly return to an annualized return.

    Args:
        monthly_return: Monthly return as a decimal (e.g. 0.01 for 1%).

    Returns:
        Annualized return: (1 + monthly_return)^12 − 1.
    """
    return (1.0 + monthly_return) ** 12 - 1.0


def monthly_return_from_annual(annual_return: float) -> float:
    """Convert an annual return to a monthly return.

    Args:
        annual_return: Annual return as a decimal (e.g. 0.10 for 10%).

    Returns:
        Monthly return: (1 + annual_return)^(1/12) − 1.
    """
    return (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
