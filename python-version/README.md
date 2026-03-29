# Theoretical Trading Portfolio Calculator

## Overview
A local Python desktop application that simulates a theoretical self-managed trading portfolio using historical stock data and a local Wolfram Mathematica 14.3 installation as the mathematical engine.

**This is a theoretical investment simulator, not a brokerage tool.**

## Features
- Forward simulation of portfolio growth using historical stock data or constant return assumptions
- Reverse solving: find unknown parameters (initial deposit, monthly deposit, equivalent returns) given a target outcome
- Local Wolfram Mathematica integration for symbolic validation and numerical solving
- Interactive PySide6 desktop GUI with charts and detailed monthly breakdowns
- CSV export of results

## Mathematical Model

The portfolio follows the recurrence relation:

```
x_(n+1) = (x_n + b) * (1 + p_n)
```

Where:
- `x_n` = portfolio value after period n
- `b` = monthly deposit (added at the **beginning** of each month before return is applied)
- `p_n` = market return in period n: `p_n = price_n / price_(n-1) - 1`
- Initial deposit `A = x_0` is present before the first return period

### Deposit Timing Convention
Monthly deposits are added at the beginning of each month **before** that month's return is applied. The initial deposit is present at time zero before the first return period.

### Equivalent Annual Return
If `r_m` is the constant monthly return: `r_y = (1 + r_m)^12 - 1`

## Solver Modes

| Mode | Description | Method |
|------|-------------|--------|
| Forward Simulation | Compute final value from all inputs | Direct recurrence |
| Solve Initial Deposit | Find required starting capital | Direct (linear) |
| Solve Monthly Deposit | Find required monthly contribution | Direct (linear) |
| Solve Monthly Return | Find equivalent constant monthly return | Newton-Raphson |
| Solve Annual Return | Find equivalent constant annual return | Newton-Raphson |
| Solve Final Amount | Compute final value (via solver path) | Direct recurrence |

### Return Modes
- **Historical Returns**: Uses real monthly returns from the selected stock ticker
- **Constant Return**: Assumes a fixed monthly return for all periods

## Prerequisites

- Python 3.10+
- Wolfram Mathematica 14.3 (local installation) — optional but recommended
- pip

## Installation

```bash
cd C:\Amp_demos\investment
pip install -r requirements.txt
```

### Mathematica Configuration
The application auto-detects Mathematica at common Windows paths. If your installation is non-standard, edit `config.py` and set `MATHEMATICA_KERNEL_PATH`.

If `wolframclient` is installed, it's used as the primary interface. Otherwise, the app falls back to subprocess calls to MathKernel.

Mathematica is used for:
- Symbolic validation of recurrence results
- Numerical solving as an alternative/verification backend
- It is NOT required for the app to function — Python handles all core math independently

## Running the Application

```bash
python app.py
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Usage Examples

### Forward Simulation with Historical Data
1. Set ticker to "SPY", date range to 2020-01-01 through 2024-12-31
2. Enter initial deposit $10,000 and monthly deposit $500
3. Select "Forward Simulation" mode and "Historical Returns"
4. Click Run

### Solve for Required Monthly Deposit
1. Select "Constant Return" mode, set monthly return to 0.8%
2. Enter initial deposit $10,000, target final value $100,000
3. Set number of periods to 60 months
4. Select "Solve for Monthly Deposit"
5. Click Run — the app solves for the monthly deposit needed

## Project Structure

```
investment/
├── app.py                          # Main entry point
├── config.py                       # Configuration (paths, defaults)
├── requirements.txt
├── README.md
├── core/
│   ├── portfolio_math.py           # Forward recurrence and math logic
│   ├── reverse_solver.py           # Newton-Raphson and reverse solving
│   └── returns.py                  # Monthly return extraction
├── gui/
│   └── main_window.py              # PySide6 desktop GUI
├── models/
│   ├── inputs.py                   # Typed input models
│   └── results.py                  # Typed result models
├── services/
│   ├── market_data.py              # Historical data fetching (yfinance)
│   └── mathematica_engine.py       # Local Mathematica integration
└── tests/
    └── test_portfolio_math.py      # Unit tests for math core
```

## Known Limitations
- Single ticker only (no multi-asset portfolio)
- No tax, commission, or inflation modeling
- Dividend tax effects not modeled
- No currency conversion
- Newton-Raphson may fail for extreme parameter combinations
- Mathematica integration requires a local installation and license
- Historical data depends on yfinance availability

## Architecture Decisions
- Python controls all application logic; Mathematica is a validation/verification layer
- Newton-Raphson implemented natively in Python for transparency
- Linear unknowns (A, b) solved directly without iteration
- GUI and math logic strictly separated via service layers
- All monetary calculations use float (sufficient for simulation purposes)
