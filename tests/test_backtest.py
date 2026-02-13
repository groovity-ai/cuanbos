"""Tests for backtest.py — verify all 3 strategies with enhanced metrics."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import json
import unittest.mock as mock
import pandas as pd
import numpy as np

# Mock database and logger before importing backtest
sys.modules.setdefault('database', mock.MagicMock())

# Mock loguru
class _FakeLogger:
    def info(self, *a, **kw): pass
    def debug(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def bind(self, **kw): return self
    def add(self, *a, **kw): return 0
    def remove(self, *a, **kw): pass

_mock_loguru = mock.MagicMock()
_mock_loguru.logger = _FakeLogger()
sys.modules['loguru'] = _mock_loguru
_mock_logger_mod = mock.MagicMock()
_mock_logger_mod.get_logger = lambda name: _FakeLogger()
sys.modules['logger'] = _mock_logger_mod

# Mock cache
_mock_cache = mock.MagicMock()
_mock_cache.cached = lambda prefix, ttl=900: lambda f: f
_mock_cache.TTL_MARKET_DATA = 300
_mock_cache.TTL_ANALYSIS = 900
_mock_cache.TTL_NEWS = 1800
_mock_cache.TTL_LLM = 3600
_mock_cache.TTL_SCREENER = 600
sys.modules['cache'] = _mock_cache


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


# Patch yfinance before importing backtest
_mock_df = _make_mock_df()
_mock_ticker = mock.MagicMock()
_mock_ticker.history.return_value = _mock_df

_mock_yf = mock.MagicMock()
_mock_yf.Ticker.return_value = _mock_ticker
sys.modules['yfinance'] = _mock_yf

# Force reimport
sys.modules.pop('backtest', None)
from backtest import run_backtest


def run_test_backtest(symbol, strategy):
    """Run backtest — now returns dict directly."""
    _mock_ticker.history.return_value = _mock_df
    _mock_yf.Ticker.return_value = _mock_ticker
    return run_backtest(symbol, strategy)


class TestBacktest:
    """Tests for the enhanced backtest engine."""

    def test_rsi_oversold_strategy(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        assert "error" not in result
        assert result["strategy"] == "rsi_oversold"
        assert "win_rate" in result
        assert "profit_pct" in result

    def test_ma_crossover_strategy(self):
        result = run_test_backtest("TEST", "ma_crossover")
        assert "error" not in result
        assert result["strategy"] == "ma_crossover"

    def test_macd_reversal_strategy(self):
        result = run_test_backtest("TEST", "macd_reversal")
        assert "error" not in result
        assert result["strategy"] == "macd_reversal"
        assert "win_rate" in result

    def test_result_has_required_fields(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        required = ["symbol", "strategy", "initial_capital", "final_value",
                     "profit_loss", "profit_pct", "trades_count", "win_rate"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_win_rate_between_0_and_100(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        assert 0 <= result["win_rate"] <= 100

    def test_enhanced_metrics_present(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        assert "metrics" in result
        metrics = result["metrics"]
        assert "sharpe_ratio" in metrics
        assert "max_drawdown_pct" in metrics
        assert "calmar_ratio" in metrics
        assert "profit_factor" in metrics
        assert "avg_win" in metrics
        assert "avg_loss" in metrics

    def test_equity_curve_present(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        assert "equity_curve" in result
        assert len(result["equity_curve"]) > 0
        first = result["equity_curve"][0]
        assert "date" in first
        assert "equity" in first

    def test_recent_trades_present(self):
        result = run_test_backtest("TEST", "rsi_oversold")
        assert "recent_trades" in result
        assert isinstance(result["recent_trades"], list)
