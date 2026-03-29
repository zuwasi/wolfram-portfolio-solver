# Project Specification

## Project name

Theoretical Trading Portfolio Calculator and Reverse Solver

## Goal

Build a local Python desktop application that simulates a theoretical self managed trading portfolio using historical stock data and a local Wolfram Mathematica 14.3 installation as the mathematical engine.

The application must support two major capabilities:

1. Forward simulation:
   Given an initial deposit, monthly deposit, selected stock ticker, investment date range, and historical market returns, calculate the final portfolio value over time using a first order difference equation.

2. Reverse engineering:
   Given all parameters except one unknown variable, solve for the unknown numerically.
   Examples:
   - Given final amount, initial deposit, and historical market behavior, solve for the required monthly deposit.
   - Given final amount, initial deposit, and constant monthly deposits, solve for an equivalent annual return.
   - Given final amount and other parameters, solve for the required initial deposit.

The system must use the local Wolfram Mathematica engine for symbolic and numerical mathematics. Python is the main application language and GUI language. The solution must run fully locally on the user's machine with no cloud dependency.

## High level concept

The app is a theoretical investment simulator, not a brokerage tool and not a live trading system. It is intended for mathematical modeling, historical backtesting, and solving inverse financial problems.

The application will:
- Load historical stock price data for one ticker at a time.
- Convert price history into periodic returns.
- Apply the difference equation recurrence over the investment horizon.
- Allow fixed monthly deposits, and a future extension path for variable deposits.
- Support solving one unknown parameter using Newton Raphson when no simple closed form is used.
- Use Mathematica for formula generation, symbolic simplification where useful, and numerical solving where appropriate.
- Present results in a clear Python desktop application.

## Mathematical model

Let:

- `A` be the initial deposit.
- `b_n` be the deposit added at each period. In the first implementation this will usually be constant, so `b_n = b`.
- `p_n` be the market return in period `n`.
- `x_n` be the portfolio value after period `n`.

The recurrence is:

`x_(n+1) = (x_n + b_n) * (1 + p_n)`

A closely related explicit formulation is:

`x_n = A * Product[(1 + p_k), {k, 0, n-1}] + Sum[b_j * Product[(1 + p_m), {m, j+1, n-1}], {j, 0, n-1}]`

Use a mathematically consistent indexing convention in the code and document it clearly.

The implementation must be careful about the exact time convention:
- Initial deposit is present before the first return period.
- Monthly deposit timing must be selectable or at least explicitly defined.
- In version 1, define monthly deposits as deposited at the beginning of each month before applying that month's return.
- This convention must be documented in the GUI and in the code comments.

## Reverse solving requirements

The application must support solving for one unknown parameter while all other parameters are known.

Version 1 must support these unknowns:
- Initial deposit `A`
- Constant monthly deposit `b`
- Equivalent constant monthly return `r_m`
- Equivalent annual return `r_y`
- Final amount `x_n`

The application must provide two solving modes:

### Mode 1: Historical return mode

Use real historical periodic returns from the selected ticker over the chosen date range.

Supported unknowns in this mode:
- `A`
- `b`
- `x_n`

In this mode, equivalent annual return is not directly taken from market data because the returns are already known period by period. However, the application may also calculate a derived annualized return from the observed result for reporting.

### Mode 2: Constant return mode

Assume a fixed monthly return for all periods.

Supported unknowns in this mode:
- `A`
- `b`
- `r_m`
- `r_y`
- `x_n`

Use Newton Raphson when the chosen unknown leads to a nonlinear equation and there is no direct trivial linear solution implemented.

If the target function is not well behaved for Newton Raphson, the app must:
- detect failure to converge,
- show a clear error message,
- optionally fall back to a more robust one dimensional method such as bisection or secant if easy to implement.

## Required mathematics engine usage

The Python application must integrate with the local Wolfram Mathematica 14.3 installation.

Primary intent:
- Use Mathematica for symbolic derivation and validation of formulas.
- Use Mathematica numerical solving when useful.
- Keep the Python side in control of the application logic and GUI.

Preferred integration order:
1. First choice: use a Python package that can communicate with the local Wolfram kernel if available on the machine.
2. If that is not practical, call the local Wolfram kernel through a subprocess interface and exchange expressions and results cleanly.
3. The implementation must remain local only.

The code must isolate the Mathematica integration behind a dedicated service layer, for example:
- `mathematica_engine.py`

This layer should expose methods such as:
- simplify symbolic formula
- validate recurrence result
- solve one variable numerically
- compute equivalent annual return from a target equation

Do not tightly couple GUI code to Mathematica calls.

## Historical data requirements

Version 1 should support one ticker at a time.

The app must fetch historical stock data from a Python accessible source suitable for local prototyping. A practical initial choice is `yfinance`, unless the user later replaces it with another provider.

Historical data requirements:
- Use adjusted close if available.
- Convert daily historical data into monthly periods.
- Monthly returns must be derived consistently from end of month adjusted close data.
- Handle non trading days correctly by using the closest valid market close in the aggregation logic.
- Store the downloaded raw data in memory and optionally allow export to CSV.

The application must clearly show:
- ticker symbol
- start date
- end date
- number of months used
- monthly return series used in calculations

## Scope of version 1

Version 1 must include:

1. Python desktop GUI.
2. Local integration with Wolfram Mathematica 14.3.
3. One ticker historical simulation.
4. Forward calculation of final portfolio value.
5. Reverse solving for one unknown.
6. Graphs of portfolio growth over time.
7. Summary table of inputs and outputs.
8. Error handling and validation.
9. Unit tests for the mathematical core.

Version 1 does not need:
- live brokerage integration
- multi ticker portfolio allocation
- taxes
- commissions
- inflation adjustment
- dividend tax modeling
- currency conversion
- optimization over multiple securities
- user accounts
- cloud services

## Recommended Python architecture

Use a clean modular structure.

Suggested modules:

- `app.py`
  Main entry point.

- `gui/`
  GUI code.

- `core/portfolio_math.py`
  Forward recurrence and mathematical logic.

- `core/reverse_solver.py`
  Newton Raphson and related solving logic.

- `core/returns.py`
  Historical return extraction and transformations.

- `services/market_data.py`
  Historical data fetching.

- `services/mathematica_engine.py`
  Local Mathematica integration layer.

- `models/inputs.py`
  Typed input models.

- `models/results.py`
  Typed result models.

- `tests/`
  Unit tests.

Use Python type hints throughout.

## Recommended GUI technology

Preferred GUI choice: PySide6.

Reason:
- modern and maintainable
- suitable for desktop financial tools
- good widget support
- easy to add tables and charts

Alternative acceptable choice:
- PyQt6

The GUI should include at minimum:

### Input section
- Ticker symbol
- Start date
- End date
- Initial deposit
- Monthly deposit
- Solver mode selector:
  - Forward simulation
  - Solve for initial deposit
  - Solve for monthly deposit
  - Solve for equivalent monthly return
  - Solve for equivalent annual return
  - Solve for final amount
- Historical return mode or constant return mode selector
- Deposit timing convention display
- Run button

### Output section
- Final value
- Total contributions
- Total growth
- Equivalent CAGR or annualized metric where applicable
- Solver convergence information
- Number of iterations
- Error or warning messages

### Visualization section
- Portfolio value over time chart
- Optional contribution versus growth stacked chart
- Optional monthly returns chart

### Diagnostics section
- Exact mathematical equation used
- Whether result was obtained directly or numerically
- Newton Raphson status
- Mathematica validation status

## Numerical solving requirements

Implement a dedicated Newton Raphson solver in Python for one dimensional problems, even if Mathematica is also used. This is important for transparency and local control.

The solver must support:
- custom initial guess
- tolerance
- maximum iteration count
- derivative by analytical formula when available
- numerical derivative fallback when needed

The solver must return:
- root value
- converged true or false
- iteration count
- final residual
- error message if not converged

Use Mathematica as a validation and optional alternative solving backend, not as a hidden black box for the whole application.

For example:
- Python computes the result
- Mathematica verifies the equation or symbolic form
- discrepancies are logged for debugging

## Mathematical details to enforce

The implementation must explicitly define and document all of the following:

1. Time step convention:
   Monthly periods.

2. Return definition:
   `p_n = (price_n / price_(n-1)) - 1`

3. Deposit convention for version 1:
   Monthly deposit occurs at the beginning of each month before return is applied.

4. Initial deposit convention:
   Present at time zero before the first return period.

5. Final value definition:
   Value after the last period return is applied.

6. Equivalent annual return conversion:
   If `r_m` is the equivalent monthly return, then
   `r_y = (1 + r_m)^12 - 1`

7. Target equation examples:
   For solving monthly deposit under constant return:
   `f(b) = final_value(A, b, r_m, n) - target_final = 0`

   For solving equivalent monthly return:
   `f(r_m) = final_value(A, b, r_m, n) - target_final = 0`

## User workflows

### Workflow 1: Forward simulation with historical data
User enters:
- ticker
- start date
- end date
- initial deposit
- monthly deposit

System:
- downloads historical data
- derives monthly returns
- runs recurrence
- displays final amount, graph, and summary

### Workflow 2: Solve for monthly deposit
User enters:
- ticker or constant return mode
- date range or number of periods
- initial deposit
- target final amount

System:
- builds the target equation
- solves for monthly deposit
- shows result and convergence diagnostics

### Workflow 3: Solve for equivalent annual return
User enters:
- constant return mode
- number of months
- initial deposit
- monthly deposit
- target final amount

System:
- solves for monthly return
- converts to annual return
- shows both monthly and annual rates

## Validation and input handling

The app must validate:
- ticker is not empty
- start date is earlier than end date
- investment period is at least one month
- deposits are not negative unless explicitly allowed later
- target final amount is positive
- number of periods is valid in constant return mode
- Newton Raphson initial guesses are reasonable

The app must show human readable validation messages.

## Charts and reporting

The app should provide:
- line chart of portfolio value versus time
- summary panel with key metrics
- optional table of monthly steps including:
  - date
  - deposit
  - return
  - portfolio value before return
  - portfolio value after return

Allow export of results to CSV.
Optional for version 1.1:
- export to PDF
- export full scenario report

## Testing requirements

Create unit tests for the mathematical core.

At minimum test:
1. Zero return case.
2. Zero monthly deposit case.
3. Constant return closed form comparison.
4. Historical return recurrence consistency.
5. Reverse solving for monthly deposit in a known simple case.
6. Reverse solving for equivalent monthly return.
7. Edge case where Newton Raphson fails to converge.
8. Agreement between Python result and Mathematica validation for selected test cases.

Use deterministic tests.

## Code quality requirements

The code must:
- be modular and readable
- use type hints
- include docstrings
- avoid hard coded machine specific paths where possible
- centralize configuration
- separate GUI, logic, data access, and Mathematica integration
- include meaningful exception handling
- include logging for debugging numerical issues

## Configuration requirements

Create a configuration file or configuration module for:
- Mathematica kernel path if needed
- default solver tolerance
- default max iterations
- default data provider settings
- default chart settings

Do not hard code a single absolute installation path unless necessary. If a path is required, detect it if possible or document how the user can change it.

## Deliverables

Produce the following:

1. Complete Python source code.
2. `requirements.txt`
3. `README.md`
4. clear setup instructions
5. test suite
6. sample screenshots if convenient
7. example usage scenario in README
8. optional sample CSV export

## README requirements

The README must explain:
- what the app does
- how the mathematics is defined
- how Mathematica is used
- how to install dependencies
- how to configure Mathematica path if needed
- how to run the app
- how to run tests
- known limitations

## Implementation priorities

Implement in this order:

### Phase 1
- mathematical core in Python
- constant return mode
- forward simulation
- reverse solving
- unit tests

### Phase 2
- local Mathematica integration
- symbolic validation
- Mathematica based optional solving

### Phase 3
- historical stock data loading
- monthly return extraction
- GUI integration

### Phase 4
- charts
- export
- diagnostics improvements

## Acceptance criteria

The work is considered successful only if all of the following are true:

1. The app runs locally on Windows with Python and a local Mathematica 14.3 installation.
2. The user can perform forward simulation using one stock ticker and historical data.
3. The user can solve at least the following unknowns:
   - initial deposit
   - monthly deposit
   - equivalent annual return in constant return mode
4. Newton Raphson works for supported nonlinear cases and reports convergence status.
5. The app clearly documents the deposit timing convention and return definition.
6. The GUI is usable and not just a command line script.
7. The code is modular and maintainable.
8. Unit tests pass.
9. The application does not depend on any cloud API for mathematics.
10. Mathematica is actually used as part of the solution and not ignored.

## Important engineering notes

Do not produce placeholder code.
Do not produce pseudo code only.
Do not leave empty methods.
Do not silently swallow exceptions.
Do not hide numerical instability.
If a result depends on assumptions, show the assumptions in the UI or logs.
Prefer correct and minimal functionality over broad but unreliable functionality.

## Explicit instruction to the coding agent

Build the application incrementally but deliver runnable code.
Start with the mathematical engine and tests before building the full GUI.
Where there is ambiguity, choose the most mathematically explicit and maintainable implementation.
Use clear comments for all recurrence and solver formulas.
At the end, provide a short summary of architectural decisions and any limitations that remain.
