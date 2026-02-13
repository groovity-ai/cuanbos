# CuanBot 💰

AI-Powered Financial Analyst Agent.

## Features
1. **Market Data**: OHLCV fetcher (Stocks & Crypto).
2. **Tech Analysis**: RSI, MACD, Moving Averages, "Gorengan" Detector.
3. **Backtesting**: Simulate strategies (RSI Oversold, MA Crossover) on historical data.
4. **Risk Monitor**: Portfolio monitoring for Stop Loss / Take Profit alerts.

## Setup
Run with Docker to ensure dependencies (pandas-ta, yfinance) are present.

```bash
docker build -t cuanbot-engine .
```

## Usage

### 1. Market Data & Analysis
```bash
docker run --rm cuanbot-engine python scripts/market_data.py BBCA.JK | \
docker run --rm -i cuanbot-engine python scripts/tech_analysis.py
```

### 2. Backtesting
```bash
# Strategies: rsi_oversold, ma_crossover
docker run --rm -v $(pwd)/src:/app/src cuanbot-engine python src/backtest.py BBCA.JK rsi_oversold
```

### 3. Risk Monitor
```bash
docker run --rm -v $(pwd)/src:/app/src cuanbot-engine python src/risk_monitor.py
```
