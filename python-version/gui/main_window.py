"""Main window for the Theoretical Trading Portfolio Calculator."""

import csv
import logging
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from models.inputs import SolverMode
from core.portfolio_math import (
    compute_annualized_return,
    compute_total_contributions,
    forward_simulation,
    forward_simulation_constant_return,
)
from core.returns import compute_monthly_returns
from core.reverse_solver import (
    solve_annual_return,
    solve_final_amount,
    solve_initial_deposit,
    solve_monthly_deposit,
    solve_monthly_return,
)
from services.market_data import fetch_historical_data

logger = logging.getLogger(__name__)

_SOLVER_MODE_MAP = {
    "Forward Simulation": SolverMode.FORWARD,
    "Solve for Initial Deposit": SolverMode.SOLVE_INITIAL_DEPOSIT,
    "Solve for Monthly Deposit": SolverMode.SOLVE_MONTHLY_DEPOSIT,
    "Solve for Monthly Return": SolverMode.SOLVE_MONTHLY_RETURN,
    "Solve for Annual Return": SolverMode.SOLVE_ANNUAL_RETURN,
    "Solve for Final Amount": SolverMode.SOLVE_FINAL_AMOUNT,
}


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Theoretical Trading Portfolio Calculator")
        self.setMinimumSize(1200, 800)

        self._last_result = None
        self._last_solver_result = None
        self._last_returns: list[float] = []
        self._last_dates: list[date] = []

        self._build_ui()
        self._connect_signals()
        self._on_return_mode_changed()
        self._on_solver_mode_changed()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT: inputs ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)

        inputs_group = QGroupBox("Inputs")
        form = QFormLayout()

        self._ticker = QLineEdit("SPY")
        form.addRow("Ticker symbol:", self._ticker)

        self._return_mode = QComboBox()
        self._return_mode.addItems(["Historical Returns", "Constant Return"])
        form.addRow("Return mode:", self._return_mode)

        today = QDate.currentDate()
        five_years_ago = today.addYears(-5)

        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDate(five_years_ago)
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Start date:", self._start_date)

        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDate(today)
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("End date:", self._end_date)

        self._num_periods = QSpinBox()
        self._num_periods.setRange(1, 600)
        self._num_periods.setValue(60)
        form.addRow("Number of periods (months):", self._num_periods)

        self._constant_return = QDoubleSpinBox()
        self._constant_return.setRange(-100.0, 100.0)
        self._constant_return.setDecimals(4)
        self._constant_return.setValue(0.8)
        self._constant_return.setSuffix(" %")
        form.addRow("Constant monthly return (%):", self._constant_return)

        self._initial_deposit = QDoubleSpinBox()
        self._initial_deposit.setRange(0.0, 1e9)
        self._initial_deposit.setDecimals(2)
        self._initial_deposit.setValue(10000.0)
        self._initial_deposit.setPrefix("$ ")
        form.addRow("Initial deposit ($):", self._initial_deposit)

        self._monthly_deposit = QDoubleSpinBox()
        self._monthly_deposit.setRange(0.0, 1e9)
        self._monthly_deposit.setDecimals(2)
        self._monthly_deposit.setValue(500.0)
        self._monthly_deposit.setPrefix("$ ")
        form.addRow("Monthly deposit ($):", self._monthly_deposit)

        self._target_value = QDoubleSpinBox()
        self._target_value.setRange(0.0, 1e9)
        self._target_value.setDecimals(2)
        self._target_value.setValue(0.0)
        self._target_value.setPrefix("$ ")
        form.addRow("Target final value ($):", self._target_value)

        self._solver_mode = QComboBox()
        self._solver_mode.addItems(list(_SOLVER_MODE_MAP.keys()))
        form.addRow("Solver mode:", self._solver_mode)

        deposit_label = QLabel(
            "Deposits added at beginning of each month before return is applied."
        )
        deposit_label.setWordWrap(True)
        deposit_label.setStyleSheet("color: #555; font-style: italic;")
        form.addRow("Deposit timing:", deposit_label)

        self._run_btn = QPushButton("Run")
        self._run_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        form.addRow(self._run_btn)

        inputs_group.setLayout(form)
        left_layout.addWidget(inputs_group)
        left_layout.addStretch()

        # --- RIGHT: outputs ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)

        self._tabs = QTabWidget()

        # Tab 1: Summary
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        self._summary_text = QTextBrowser()
        self._summary_text.setOpenExternalLinks(False)
        summary_layout.addWidget(self._summary_text)
        self._export_btn = QPushButton("Export CSV")
        self._export_btn.setEnabled(False)
        summary_layout.addWidget(self._export_btn)
        self._tabs.addTab(summary_tab, "Summary")

        # Tab 2: Chart
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        self._figure = Figure(figsize=(10, 6), dpi=100)
        self._canvas = FigureCanvasQTAgg(self._figure)
        chart_layout.addWidget(self._canvas)
        self._tabs.addTab(chart_tab, "Chart")

        # Tab 3: Monthly Details
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Period", "Date", "Deposit", "Return (%)",
            "Value Before Return", "Value After Return",
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._tabs.addTab(self._table, "Monthly Details")

        # Tab 4: Diagnostics
        self._diagnostics_text = QTextBrowser()
        self._tabs.addTab(self._diagnostics_text, "Diagnostics")

        right_layout.addWidget(self._tabs)

        # Splitter setup
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._return_mode.currentIndexChanged.connect(self._on_return_mode_changed)
        self._solver_mode.currentIndexChanged.connect(self._on_solver_mode_changed)
        self._run_btn.clicked.connect(self._on_run)
        self._export_btn.clicked.connect(self._on_export_csv)

    # ------------------------------------------------------------------
    # Dynamic enable / disable
    # ------------------------------------------------------------------

    def _on_return_mode_changed(self) -> None:
        historical = self._return_mode.currentText() == "Historical Returns"
        self._ticker.setEnabled(historical)
        self._start_date.setEnabled(historical)
        self._end_date.setEnabled(historical)
        self._num_periods.setEnabled(not historical)
        self._constant_return.setEnabled(not historical)

        # Re-evaluate solver mode constraints
        self._on_solver_mode_changed()

    def _on_solver_mode_changed(self) -> None:
        mode = _SOLVER_MODE_MAP[self._solver_mode.currentText()]
        historical = self._return_mode.currentText() == "Historical Returns"

        # Default: everything enabled that the return mode allows
        self._initial_deposit.setEnabled(True)
        self._monthly_deposit.setEnabled(True)
        self._target_value.setEnabled(True)

        if mode == SolverMode.FORWARD:
            self._target_value.setEnabled(False)
        elif mode == SolverMode.SOLVE_INITIAL_DEPOSIT:
            self._initial_deposit.setEnabled(False)
        elif mode == SolverMode.SOLVE_MONTHLY_DEPOSIT:
            self._monthly_deposit.setEnabled(False)
        elif mode in (SolverMode.SOLVE_MONTHLY_RETURN, SolverMode.SOLVE_ANNUAL_RETURN):
            if historical:
                # These modes only work in constant return mode
                self._return_mode.setCurrentText("Constant Return")
                self._on_return_mode_changed()
                return
        elif mode == SolverMode.SOLVE_FINAL_AMOUNT:
            self._target_value.setEnabled(False)

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        try:
            self._run_simulation()
        except Exception as exc:
            logger.exception("Simulation failed")
            QMessageBox.critical(self, "Error", str(exc))
            self._status.showMessage("Simulation failed")

    def _run_simulation(self) -> None:
        mode = _SOLVER_MODE_MAP[self._solver_mode.currentText()]
        historical = self._return_mode.currentText() == "Historical Returns"

        initial_deposit = self._initial_deposit.value()
        monthly_deposit = self._monthly_deposit.value()
        target_final = self._target_value.value()

        # ---- Build returns list and dates ----
        if historical:
            self._status.showMessage("Fetching market data…")
            start = self._start_date.date().toPython()
            end = self._end_date.date().toPython()
            ticker = self._ticker.text().strip().upper()
            if not ticker:
                raise ValueError("Ticker symbol cannot be empty.")
            prices = fetch_historical_data(ticker, start, end)
            dated_returns = compute_monthly_returns(prices)
            dates = [d for d, _ in dated_returns]
            returns = [r for _, r in dated_returns]
            num_periods = len(returns)
        else:
            num_periods = self._num_periods.value()
            monthly_ret = self._constant_return.value() / 100.0
            returns = [monthly_ret] * num_periods
            base = date.today()
            dates = [
                date(
                    base.year + (base.month + i - 1) // 12,
                    (base.month + i - 1) % 12 + 1,
                    1,
                )
                for i in range(num_periods)
            ]

        self._status.showMessage("Running simulation…")

        solver_result = None
        diag_equation = ""
        diag_method = "Direct forward simulation"

        # ---- Solver dispatch ----
        if mode == SolverMode.FORWARD:
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = "x_(n+1) = (x_n + b) * (1 + p_n)"

        elif mode == SolverMode.SOLVE_INITIAL_DEPOSIT:
            solver_result = solve_initial_deposit(
                monthly_deposit, returns, target_final, 1e-10, 1000,
            )
            initial_deposit = solver_result.value
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = "A = (target − b·Σ∏(1+p_j)) / ∏(1+p_i)"
            diag_method = "Closed-form (linear in A)"

        elif mode == SolverMode.SOLVE_MONTHLY_DEPOSIT:
            solver_result = solve_monthly_deposit(
                initial_deposit, returns, target_final, 1e-10, 1000,
            )
            monthly_deposit = solver_result.value
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = "b = (target − A·∏(1+p_i)) / Σ∏(1+p_j)"
            diag_method = "Closed-form (linear in b)"

        elif mode == SolverMode.SOLVE_MONTHLY_RETURN:
            solver_result = solve_monthly_return(
                initial_deposit, monthly_deposit, num_periods, target_final,
                1e-10, 1000,
            )
            monthly_ret_solved = solver_result.value
            returns = [monthly_ret_solved] * num_periods
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = "f(r) = forward(A, b, r, N) − target = 0"
            diag_method = "Newton-Raphson (nonlinear in r)"

        elif mode == SolverMode.SOLVE_ANNUAL_RETURN:
            solver_result = solve_annual_return(
                initial_deposit, monthly_deposit, num_periods, target_final,
                1e-10, 1000,
            )
            annual_ret_solved = solver_result.value
            monthly_ret_solved = (1.0 + annual_ret_solved) ** (1.0 / 12.0) - 1.0
            returns = [monthly_ret_solved] * num_periods
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = (
                "f(r_y) = forward(A, b, (1+r_y)^(1/12)−1, N) − target = 0"
            )
            diag_method = "Newton-Raphson (nonlinear in r_y)"

        elif mode == SolverMode.SOLVE_FINAL_AMOUNT:
            solver_result = solve_final_amount(initial_deposit, monthly_deposit, returns)
            values = forward_simulation(initial_deposit, monthly_deposit, returns)
            diag_equation = "x_(n+1) = (x_n + b) * (1 + p_n)  [trivial forward]"
            diag_method = "Direct forward simulation (through solver path)"

        else:
            raise ValueError(f"Unknown solver mode: {mode}")

        # ---- Build result ----
        final_value = values[-1]
        total_contributions = compute_total_contributions(
            initial_deposit, monthly_deposit, num_periods,
        )
        total_growth = final_value - total_contributions

        try:
            cagr = compute_annualized_return(
                values, initial_deposit, total_contributions, num_periods,
            )
        except ValueError:
            cagr = None

        self._last_result = {
            "final_value": final_value,
            "total_contributions": total_contributions,
            "total_growth": total_growth,
            "cagr": cagr,
            "num_periods": num_periods,
            "values": values,
            "returns": returns,
            "dates": dates,
            "initial_deposit": initial_deposit,
            "monthly_deposit": monthly_deposit,
        }
        self._last_solver_result = solver_result
        self._last_returns = returns
        self._last_dates = dates

        # ---- Update tabs ----
        self._update_summary(
            final_value, total_contributions, total_growth, cagr,
            num_periods, solver_result, mode, initial_deposit, monthly_deposit,
        )
        self._update_chart(values, dates, total_contributions, initial_deposit, monthly_deposit)
        self._update_table(values, returns, dates, monthly_deposit)
        self._update_diagnostics(
            diag_equation, diag_method, solver_result, values, returns,
            initial_deposit, monthly_deposit,
        )

        self._export_btn.setEnabled(True)
        self._status.showMessage("Simulation complete")

    # ------------------------------------------------------------------
    # Tab updates
    # ------------------------------------------------------------------

    def _update_summary(
        self,
        final_value: float,
        total_contributions: float,
        total_growth: float,
        cagr: float | None,
        num_periods: int,
        solver_result,
        mode: SolverMode,
        initial_deposit: float,
        monthly_deposit: float,
    ) -> None:
        growth_pct = (
            (total_growth / total_contributions * 100.0)
            if total_contributions > 0
            else 0.0
        )
        cagr_str = f"{cagr * 100:.4f} %" if cagr is not None else "N/A"

        lines = [
            "<h2>Simulation Results</h2>",
            "<table style='font-size:13px; border-collapse:collapse;' cellpadding='4'>",
            f"<tr><td><b>Final Portfolio Value:</b></td><td style='text-align:right'>${final_value:,.2f}</td></tr>",
            f"<tr><td><b>Total Contributions:</b></td><td style='text-align:right'>${total_contributions:,.2f}</td></tr>",
            f"<tr><td><b>Total Growth:</b></td><td style='text-align:right'>${total_growth:,.2f}</td></tr>",
            f"<tr><td><b>Growth Percentage:</b></td><td style='text-align:right'>{growth_pct:.2f} %</td></tr>",
            f"<tr><td><b>Annualized Return (CAGR):</b></td><td style='text-align:right'>{cagr_str}</td></tr>",
            f"<tr><td><b>Number of Periods:</b></td><td style='text-align:right'>{num_periods}</td></tr>",
            f"<tr><td><b>Deposit Timing:</b></td><td>Beginning of month</td></tr>",
            f"<tr><td><b>Initial Deposit:</b></td><td style='text-align:right'>${initial_deposit:,.2f}</td></tr>",
            f"<tr><td><b>Monthly Deposit:</b></td><td style='text-align:right'>${monthly_deposit:,.2f}</td></tr>",
            "</table>",
        ]

        if solver_result is not None:
            lines.append("<h3>Solver Info</h3>")
            lines.append("<table style='font-size:13px;' cellpadding='4'>")
            lines.append(
                f"<tr><td><b>Solver Mode:</b></td><td>{mode.value}</td></tr>"
            )
            lines.append(
                f"<tr><td><b>Solved Value:</b></td><td>{solver_result.value:,.6f}</td></tr>"
            )
            lines.append(
                f"<tr><td><b>Converged:</b></td><td>{solver_result.converged}</td></tr>"
            )
            lines.append(
                f"<tr><td><b>Iterations:</b></td><td>{solver_result.iterations}</td></tr>"
            )
            lines.append(
                f"<tr><td><b>Final Residual:</b></td><td>{solver_result.final_residual:.2e}</td></tr>"
            )
            if solver_result.error_message:
                lines.append(
                    f"<tr><td><b>Error:</b></td><td style='color:red'>{solver_result.error_message}</td></tr>"
                )
            lines.append("</table>")

        self._summary_text.setHtml("\n".join(lines))

    def _update_chart(
        self,
        values: list[float],
        dates: list,
        total_contributions: float,
        initial_deposit: float,
        monthly_deposit: float,
    ) -> None:
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        # X-axis: period indices (values has length num_periods + 1)
        num_periods = len(values) - 1
        x_labels = ["Start"] + [
            str(d) if not isinstance(d, str) else d for d in dates
        ]
        x = list(range(len(values)))

        # Cumulative contributions at each step
        cum_contributions = [initial_deposit]
        for i in range(1, len(values)):
            cum_contributions.append(cum_contributions[-1] + monthly_deposit)

        ax.plot(x, values, label="Portfolio Value", linewidth=2, color="#1f77b4")
        ax.plot(
            x, cum_contributions, label="Cumulative Contributions",
            linewidth=1.5, linestyle="--", color="#2ca02c",
        )
        ax.fill_between(x, cum_contributions, values, alpha=0.15, color="#1f77b4")

        ax.set_title("Portfolio Value Over Time", fontsize=14, fontweight="bold")
        ax.set_xlabel("Period")
        ax.set_ylabel("Value ($)")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)

        # Show a subset of x-tick labels to avoid crowding
        if num_periods > 20:
            step = max(num_periods // 10, 1)
            tick_positions = list(range(0, len(x), step))
            if (len(x) - 1) not in tick_positions:
                tick_positions.append(len(x) - 1)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(
                [x_labels[i] if i < len(x_labels) else "" for i in tick_positions],
                rotation=45, ha="right", fontsize=8,
            )
        else:
            ax.set_xticks(x)
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)

        self._figure.tight_layout()
        self._canvas.draw()

    def _update_table(
        self,
        values: list[float],
        returns: list[float],
        dates: list,
        monthly_deposit: float,
    ) -> None:
        num_periods = len(returns)
        self._table.setRowCount(num_periods)

        for i in range(num_periods):
            value_before = values[i] + monthly_deposit
            value_after = values[i + 1]
            ret_pct = returns[i] * 100.0
            date_str = str(dates[i]) if i < len(dates) else ""

            self._table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._table.setItem(i, 1, QTableWidgetItem(date_str))
            self._table.setItem(i, 2, QTableWidgetItem(f"${monthly_deposit:,.2f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"{ret_pct:.4f}"))
            self._table.setItem(i, 4, QTableWidgetItem(f"${value_before:,.2f}"))
            self._table.setItem(i, 5, QTableWidgetItem(f"${value_after:,.2f}"))

        self._table.resizeColumnsToContents()

    def _update_diagnostics(
        self,
        equation: str,
        method: str,
        solver_result,
        values: list[float],
        returns: list[float],
        initial_deposit: float,
        monthly_deposit: float,
    ) -> None:
        lines = [
            "<h2>Diagnostics</h2>",
            f"<p><b>Mathematical Equation:</b> {equation}</p>",
            f"<p><b>Solution Method:</b> {method}</p>",
        ]

        if solver_result is not None:
            lines.append("<h3>Newton-Raphson / Solver Status</h3>")
            lines.append(f"<p>Converged: <b>{solver_result.converged}</b></p>")
            lines.append(f"<p>Iterations: <b>{solver_result.iterations}</b></p>")
            lines.append(
                f"<p>Final Residual: <b>{solver_result.final_residual:.2e}</b></p>"
            )
            if solver_result.error_message:
                lines.append(
                    f"<p style='color:red'>Error: {solver_result.error_message}</p>"
                )
        else:
            lines.append("<p>No iterative solver was used (direct computation).</p>")

        # Mathematica validation (optional — app works fully without it)
        lines.append("<h3>Mathematica Validation</h3>")
        try:
            from services.mathematica_engine import validate_recurrence, _wolframscript_path, _kernel_path, _USE_WOLFRAMCLIENT

            if not (_USE_WOLFRAMCLIENT or _wolframscript_path() or _kernel_path()):
                lines.append(
                    "<p style='color:gray'>Mathematica not installed — "
                    "all calculations performed by Python engine.</p>"
                )
            else:
                result = validate_recurrence(
                    initial_deposit, monthly_deposit, returns, values[-1],
                )
                if result.get("error"):
                    lines.append(
                        f"<p style='color:orange'>Mathematica validation failed: {result['error']}</p>"
                    )
                else:
                    lines.append(
                        f"<p>Mathematica result: <b>{result['mathematica_result']:.6f}</b></p>"
                    )
                    lines.append(
                        f"<p>Python result: <b>{result['expected']:.6f}</b></p>"
                    )
                    lines.append(
                        f"<p>Difference: <b>{result['difference']:.2e}</b></p>"
                    )
                    valid_color = "green" if result["valid"] else "red"
                    lines.append(
                        f"<p style='color:{valid_color}'>Valid: <b>{result['valid']}</b></p>"
                    )
        except Exception:
            lines.append(
                "<p style='color:gray'>Mathematica not available — "
                "all calculations performed by Python engine.</p>"
            )

        self._diagnostics_text.setHtml("\n".join(lines))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export_csv(self) -> None:
        if self._last_result is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Monthly Details", "portfolio_details.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            values = self._last_result["values"]
            returns = self._last_result["returns"]
            dates = self._last_result["dates"]
            monthly_deposit = self._last_result["monthly_deposit"]

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Period", "Date", "Deposit", "Return (%)",
                    "Value Before Return", "Value After Return",
                ])
                for i in range(len(returns)):
                    value_before = values[i] + monthly_deposit
                    value_after = values[i + 1]
                    ret_pct = returns[i] * 100.0
                    date_str = str(dates[i]) if i < len(dates) else ""
                    writer.writerow([
                        i + 1, date_str, f"{monthly_deposit:.2f}",
                        f"{ret_pct:.4f}", f"{value_before:.2f}",
                        f"{value_after:.2f}",
                    ])

            self._status.showMessage(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))
