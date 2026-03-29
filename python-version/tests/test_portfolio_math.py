"""Unit tests for the mathematical core."""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.portfolio_math import (
    forward_simulation,
    forward_simulation_constant_return,
    compute_annualized_return,
    compute_total_contributions,
)
from core.reverse_solver import (
    newton_raphson,
    bisection_fallback,
    solve_initial_deposit,
    solve_monthly_deposit,
    solve_monthly_return,
    solve_annual_return,
    solve_final_amount,
)


class TestForwardSimulation:
    """Tests for forward recurrence: x_(n+1) = (x_n + b) * (1 + p_n)."""

    def test_zero_return(self):
        """With zero returns, portfolio = initial + sum of deposits."""
        values = forward_simulation(1000.0, 100.0, [0.0, 0.0, 0.0])
        assert len(values) == 4  # initial + 3 periods
        assert values[0] == 1000.0
        # Period 1: (1000 + 100) * 1.0 = 1100
        assert abs(values[1] - 1100.0) < 1e-10
        # Period 2: (1100 + 100) * 1.0 = 1200
        assert abs(values[2] - 1200.0) < 1e-10
        # Period 3: (1200 + 100) * 1.0 = 1300
        assert abs(values[3] - 1300.0) < 1e-10

    def test_zero_monthly_deposit(self):
        """With zero monthly deposit, portfolio grows only by returns."""
        values = forward_simulation(1000.0, 0.0, [0.10, 0.05, -0.03])
        assert len(values) == 4
        assert values[0] == 1000.0
        # Period 1: 1000 * 1.10 = 1100
        assert abs(values[1] - 1100.0) < 1e-10
        # Period 2: 1100 * 1.05 = 1155
        assert abs(values[2] - 1155.0) < 1e-10
        # Period 3: 1155 * 0.97 = 1120.35
        assert abs(values[3] - 1120.35) < 1e-10

    def test_constant_return_matches_formula(self):
        """Constant return simulation should match the closed-form result."""
        A, b, r, n = 1000.0, 200.0, 0.01, 12
        values = forward_simulation_constant_return(A, b, r, n)
        # Verify via manual recurrence
        x = A
        for _ in range(n):
            x = (x + b) * (1 + r)
        assert abs(values[-1] - x) < 1e-10

    def test_historical_return_recurrence_consistency(self):
        """Forward simulation step-by-step should match batch result."""
        returns = [0.02, -0.01, 0.03, 0.005, -0.02, 0.01]
        A, b = 5000.0, 500.0
        values = forward_simulation(A, b, returns)
        # Verify manually
        x = A
        for p in returns:
            x = (x + b) * (1 + p)
        assert abs(values[-1] - x) < 1e-10

    def test_single_period(self):
        """Single period simulation."""
        values = forward_simulation(1000.0, 100.0, [0.05])
        assert len(values) == 2
        assert values[0] == 1000.0
        # (1000 + 100) * 1.05 = 1155
        assert abs(values[1] - 1155.0) < 1e-10


class TestTotalContributions:
    def test_basic(self):
        assert compute_total_contributions(1000.0, 200.0, 12) == 1000.0 + 200.0 * 12


class TestNewtonRaphson:
    def test_simple_root(self):
        """Solve x^2 - 4 = 0 starting from x=1."""
        result = newton_raphson(lambda x: x**2 - 4, 1.0, 1e-12, 100)
        assert result.converged
        assert abs(result.value - 2.0) < 1e-10

    def test_with_analytical_derivative(self):
        """Solve x^2 - 4 = 0 with analytical derivative."""
        result = newton_raphson(
            lambda x: x**2 - 4, 1.0, 1e-12, 100, df=lambda x: 2 * x
        )
        assert result.converged
        assert abs(result.value - 2.0) < 1e-10

    def test_failure_to_converge(self):
        """Test convergence failure with very few iterations."""
        result = newton_raphson(lambda x: x**2 - 4, 100.0, 1e-12, 2)
        assert not result.converged
        assert result.error_message is not None


class TestBisection:
    def test_simple_root(self):
        result = bisection_fallback(lambda x: x**2 - 4, 0.0, 5.0, 1e-10, 1000)
        assert result.converged
        assert abs(result.value - 2.0) < 1e-8


class TestReverseSolving:
    def test_solve_initial_deposit_constant(self):
        """Solve for A given known final value under constant return."""
        A, b, r, n = 1000.0, 200.0, 0.01, 12
        values = forward_simulation_constant_return(A, b, r, n)
        target = values[-1]
        returns = [r] * n
        result = solve_initial_deposit(b, returns, target, 1e-10, 100)
        assert result.converged
        assert abs(result.value - A) < 1e-6

    def test_solve_monthly_deposit_constant(self):
        """Solve for b given known final value under constant return."""
        A, b, r, n = 1000.0, 200.0, 0.01, 12
        values = forward_simulation_constant_return(A, b, r, n)
        target = values[-1]
        returns = [r] * n
        result = solve_monthly_deposit(A, returns, target, 1e-10, 100)
        assert result.converged
        assert abs(result.value - b) < 1e-6

    def test_solve_monthly_return(self):
        """Solve for r_m given known final value."""
        A, b, r, n = 1000.0, 200.0, 0.01, 24
        values = forward_simulation_constant_return(A, b, r, n)
        target = values[-1]
        result = solve_monthly_return(A, b, n, target, 1e-10, 1000, initial_guess=0.005)
        assert result.converged
        assert abs(result.value - r) < 1e-6

    def test_solve_annual_return(self):
        """Solve for r_y given known final value."""
        r_y = 0.10  # 10% annual
        r_m = (1 + r_y) ** (1 / 12) - 1
        A, b, n = 1000.0, 200.0, 24
        values = forward_simulation_constant_return(A, b, r_m, n)
        target = values[-1]
        result = solve_annual_return(A, b, n, target, 1e-10, 1000, initial_guess=0.08)
        assert result.converged
        assert abs(result.value - r_y) < 1e-5

    def test_solve_initial_deposit_historical(self):
        """Solve for A with historical (variable) returns."""
        A, b = 5000.0, 300.0
        returns = [0.02, -0.01, 0.03, 0.005, -0.02, 0.015]
        values = forward_simulation(A, b, returns)
        target = values[-1]
        result = solve_initial_deposit(b, returns, target, 1e-10, 100)
        assert result.converged
        assert abs(result.value - A) < 1e-6

    def test_solve_monthly_deposit_historical(self):
        """Solve for b with historical (variable) returns."""
        A, b = 5000.0, 300.0
        returns = [0.02, -0.01, 0.03, 0.005, -0.02, 0.015]
        values = forward_simulation(A, b, returns)
        target = values[-1]
        result = solve_monthly_deposit(A, returns, target, 1e-10, 100)
        assert result.converged
        assert abs(result.value - b) < 1e-6

    def test_solve_final_amount(self):
        """Solve for final amount is just forward simulation."""
        returns = [0.01, 0.02, -0.005]
        result = solve_final_amount(1000.0, 100.0, returns)
        assert result.converged
        values = forward_simulation(1000.0, 100.0, returns)
        assert abs(result.value - values[-1]) < 1e-10
