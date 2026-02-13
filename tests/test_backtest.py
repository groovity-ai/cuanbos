"""Tests for backtest.py — verify all 3 strategies exist and produce valid output."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import json
import io
import contextlib
import unittest.mock as mock
import pandas as pd
import numpy as np

# Mock database module before importing backtest
sys.modules['database'] = mock.MagicMock()


def _make_mock_df():
    """Create a realistic mock DataFrame for backtesting."""
    np.random.seed(42)
    n = 1300  # ~5 years of trading days
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    
    prices = [10000.0]
    for i in range(1, n):
        change = np.random.normal(0.0005, 0.015)
        prices.append(prices[-1] * (1 + change))
    
    return pd.DataFrame({
        "Open": [p * 0.998 for p in prices],
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [int(np.random.uniform(1e6, 5e6)) for _ in range(n)],
    }, index=dates)


# Patch yfinance at module level BEFORE importing backtest
_mock_df = _make_mock_df()
_mock_ticker = mock.MagicMock()
_mock_ticker.history.return_value = _mock_df

_mock_yf = mock.MagicMock()
_mock_yf.Ticker.return_value = _mock_ticker
sys.modules['yfinance'] = _mock_yf

# Now import backtest (it will use our mocked yfinance)
# Force reimport if already cached
if 'backtest' in sys.modules:
    del sys.modules['backtest']

from backtest import run_backtest


def capture_backtest(symbol, strategy):
    """Run backtest and capture JSON output."""
    # Reset mock for each call
    _mock_ticker.history.return_value = _mock_df
    _mock_yf.Ticker.return_value = _mock_ticker
    
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        run_backtest(symbol, strategy)
    return f.getvalue()


class TestBacktest:
    """Tests for the backtest engine."""

    def test_rsi_oversold_strategy(self):
        output = capture_backtest("TEST", "rsi_oversold")
        result = json.loads(output)
        assert "error" not in result
        assert result["strategy"] == "rsi_oversold"
        assert "win_rate" in result
        assert "profit_pct" in result

    def test_ma_crossover_strategy(self):
        output = capture_backtest("TEST", "ma_crossover")
        result = json.loads(output)
        assert "error" not in result
        assert result["strategy"] == "ma_crossover"

    def test_macd_reversal_strategy(self):
        output = capture_backtest("TEST", "macd_reversal")
        result = json.loads(output)
        assert "error" not in result
        assert result["strategy"] == "macd_reversal"
        assert "win_rate" in result

    def test_result_has_required_fields(self):
        output = capture_backtest("TEST", "rsi_oversold")
        result = json.loads(output)
        required = ["symbol", "strategy", "initial_capital", "final_value",
                     "profit_loss", "profit_pct", "trades_count", "win_rate"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_win_rate_between_0_and_100(self):
        output = capture_backtest("TEST", "rsi_oversold")
        result = json.loads(output)
        assert 0 <= result["win_rate"] <= 100
