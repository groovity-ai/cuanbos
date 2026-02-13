"""Tests for tech_analysis.py using synthetic OHLCV data."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import pandas as pd
import numpy as np


def make_ohlcv(n=300, base_price=10000, trend="flat"):
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    np.random.seed(42)
    
    prices = [base_price]
    for i in range(1, n):
        if trend == "up":
            change = np.random.normal(0.002, 0.01)
        elif trend == "down":
            change = np.random.normal(-0.002, 0.01)
        else:
            change = np.random.normal(0, 0.01)
        prices.append(prices[-1] * (1 + change))
    
    records = []
    for i, (d, p) in enumerate(zip(dates, prices)):
        records.append({
            "Date": d.strftime("%Y-%m-%d"),
            "Open": round(p * 0.998, 2),
            "High": round(p * 1.01, 2),
            "Low": round(p * 0.99, 2),
            "Close": round(p, 2),
            "Volume": int(np.random.uniform(1e6, 5e6)),
        })
    return records


def make_gorengan_ohlcv(n=300, base_price=500):
    """Generate data that should trigger gorengan detection (volume spike + high volatility)."""
    records = make_ohlcv(n, base_price)
    # Spike volume on the last day (50x normal)
    records[-1]["Volume"] = int(records[-1]["Volume"] * 50)
    # Make last few days highly volatile
    for i in range(-5, 0):
        records[i]["Close"] = records[i]["Close"] * np.random.choice([1.15, 0.85])
        records[i]["High"] = records[i]["Close"] * 1.05
        records[i]["Low"] = records[i]["Close"] * 0.95
    return records


# --- Patch database to avoid real DB calls ---
import unittest.mock as mock

# Mock save_analysis before importing tech_analysis
with mock.patch.dict('sys.modules', {'database': mock.MagicMock()}):
    from tech_analysis import analyze_market_data


class TestAnalyzeMarketData:
    """Tests for the analyze_market_data function."""

    def test_basic_analysis_returns_verdict(self):
        data = {"symbol": "TEST", "type": "stock", "ohlcv": make_ohlcv()}
        result = analyze_market_data(data)
        assert "error" not in result
        assert "verdict" in result
        assert "price" in result
        assert "trend" in result
        assert "momentum" in result

    def test_trend_has_required_fields(self):
        data = {"symbol": "TEST", "type": "stock", "ohlcv": make_ohlcv()}
        result = analyze_market_data(data)
        trend = result["trend"]
        assert "status" in trend
        assert "ma50" in trend
        assert "ma200" in trend
        assert "golden_cross" in trend
        assert "death_cross" in trend

    def test_momentum_has_rsi(self):
        data = {"symbol": "TEST", "type": "stock", "ohlcv": make_ohlcv()}
        result = analyze_market_data(data)
        assert "rsi" in result["momentum"]
        # RSI should be between 0 and 100
        rsi = result["momentum"]["rsi"]
        assert 0 <= rsi <= 100

    def test_empty_ohlcv_returns_error(self):
        data = {"symbol": "TEST", "ohlcv": []}
        result = analyze_market_data(data)
        assert "error" in result

    def test_missing_ohlcv_returns_error(self):
        data = {"symbol": "TEST"}
        result = analyze_market_data(data)
        assert "error" in result

    def test_gorengan_detection_with_spike(self):
        data = {
            "symbol": "GORENGAN",
            "type": "stock",
            "fundamentals": {"market_cap": 500_000_000_000, "pe_ratio": -5, "pb_ratio": 0.3},
            "ohlcv": make_gorengan_ohlcv(),
        }
        result = analyze_market_data(data)
        assert "anomalies" in result
        # Should detect volume spike at minimum
        assert result["anomalies"]["volume_ratio"] > 5

    def test_bullish_trend_detected(self):
        data = {"symbol": "BULL", "type": "stock", "ohlcv": make_ohlcv(trend="up")}
        result = analyze_market_data(data)
        assert "Bullish" in result["trend"]["status"]

    def test_bearish_trend_detected(self):
        data = {"symbol": "BEAR", "type": "stock", "ohlcv": make_ohlcv(trend="down")}
        result = analyze_market_data(data)
        assert "Bearish" in result["trend"]["status"]
