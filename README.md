# Wolfram Portfolio Solver

A theoretical trading portfolio simulator powered **entirely by Wolfram Mathematica**. Every mathematical operation — forward simulation, reverse solving, root-finding — runs through the local Wolfram kernel via `wolframscript`.

## What It Does

- **Forward simulation**: Given initial deposit, monthly contributions, and a stock ticker, compute portfolio growth using historical market data
- **Reverse solving**: Given a target final value, solve for the unknown — initial deposit, monthly deposit, or equivalent return rate
- **Two solving engines**: Mathematica `Solve[]` for linear unknowns (exact), `FindRoot[]` for nonlinear unknowns (numerical)

## Mathematical Model

```
x_(n+1) = (x_n + b) × (1 + p_n)
```

- Deposits added at **beginning of each month** before return is applied
- Returns derived from adjusted close prices: `p_n = price_n / price_(n-1) - 1`
- Annual ↔ monthly return conversion: `r_y = (1 + r_m)^12 - 1`

## Two Versions Included

| Version | Location | Math Engine | Requires Mathematica? |
|---------|----------|-------------|----------------------|
| **Mathematica** | Root directory | Wolfram kernel via wolframscript | ✅ Yes |
| **Python-only** | `python-version/` | NumPy-free pure Python | ❌ No |

## Quick Start

### Mathematica Version
```bash
pip install -r requirements.txt
python app.py
```

### Python-Only Version
```bash
cd python-version
pip install -r requirements.txt
python app.py
```

## Requirements

- Python 3.10+
- PySide6, matplotlib, pandas, yfinance
- Wolfram Mathematica 14.x (for the Mathematica version)

## Presentation

Open `presentation.html` in any browser for a detailed technical walkthrough (mobile-ready, swipe-enabled).

## License

MIT
