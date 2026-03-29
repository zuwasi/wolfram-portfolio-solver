"""Historical market data service using yfinance."""
import logging
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_historical_data(
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch historical adjusted close prices for a ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'SPY').
        start_date: Start of the date range.
        end_date: End of the date range.
        
    Returns:
        DataFrame with DatetimeIndex and 'Adj Close' column.
        
    Raises:
        ValueError: If no data is returned for the ticker/date range.
    """
    logger.info("Fetching data for %s from %s to %s", ticker, start_date, end_date)
    df = yf.download(
        ticker,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        auto_adjust=False,
        progress=False,
    )
    if df is None or df.empty:
        raise ValueError(
            f"No historical data found for '{ticker}' "
            f"between {start_date} and {end_date}."
        )
    # Handle multi-level columns from newer yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Use 'Adj Close' if available, else 'Close'
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    result = df[[col]].copy()
    result.columns = ["Adj Close"]
    result.index = pd.to_datetime(result.index)
    logger.info("Fetched %d daily records for %s", len(result), ticker)
    return result


def export_to_csv(df: pd.DataFrame, path: str) -> None:
    """Export a DataFrame to CSV."""
    df.to_csv(path)
    logger.info("Exported data to %s", path)
