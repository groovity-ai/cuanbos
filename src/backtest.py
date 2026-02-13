"""
Enhanced backtesting engine for CuanBot.
Supports RSI, MA Crossover, MACD Reversal strategies
with advanced metrics: Sharpe, Max Drawdown, Calmar, Profit Factor.
"""

import sys
import json
import math
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from logger import get_logger

log = get_logger("backtest")


def run_backtest(symbol, strategy, initial_capital=10_000_000):
    """
    Run a backtest and return a dict with results + advanced metrics.
    Returns dict (not print).
    """
    try:
        # Fetch 5 years of data
        df = yf.Ticker(symbol).history(period="5y")
        if df.empty:
            return {"error": f"No data found for {symbol}"}

        log.info(f"Backtest: {symbol} / {strategy} / {len(df)} bars")

        # Calculate Indicators
        df['RSI'] = df.ta.rsi(length=14)
        df['MA50'] = df.ta.sma(length=50)
        df['MA200'] = df.ta.sma(length=200)

        macd = df.ta.macd(fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_Signal'] = macd['MACDs_12_26_9']

        # --- Simulation ---
        capital = initial_capital
        position = 0  # shares held
        entry_price = 0
        trades = []
        equity_curve = []  # daily equity snapshots

        for i in range(len(df)):
            row = df.iloc[i]
            price = row['Close']
            date = str(row.name.date()) if hasattr(row.name, 'date') else str(row.name)

            # Track equity
            current_equity = capital if position == 0 else position * price
            equity_curve.append({"date": date, "equity": round(current_equity, 2)})

            if i < 200:
                continue  # Skip warmup

            prev = df.iloc[i - 1]
            signal = "hold"

            # --- Strategy Logic ---
            if strategy == "rsi_oversold":
                if position == 0 and prev['RSI'] < 30:
                    signal = "buy"
                elif position > 0 and prev['RSI'] > 70:
                    signal = "sell"

            elif strategy == "ma_crossover":
                prev2 = df.iloc[i - 2]
                if position == 0 and prev['MA50'] > prev['MA200'] and prev2['MA50'] <= prev2['MA200']:
                    signal = "buy"
                elif position > 0 and prev['MA50'] < prev['MA200']:
                    signal = "sell"

            elif strategy == "macd_reversal":
                prev2 = df.iloc[i - 2]
                if position == 0 and prev['MACD'] > prev['MACD_Signal'] and prev2['MACD'] <= prev2['MACD_Signal']:
                    signal = "buy"
                elif position > 0 and prev['MACD'] < prev['MACD_Signal'] and prev2['MACD'] >= prev2['MACD_Signal']:
                    signal = "sell"

            # --- Execute ---
            if signal == "buy" and position == 0:
                position = capital / price
                entry_price = price
                capital = 0
                trades.append({"type": "buy", "date": date, "price": round(price, 2)})

            elif signal == "sell" and position > 0:
                exit_price = price
                profit = (exit_price - entry_price) * position
                capital = position * exit_price
                position = 0
                trades.append({
                    "type": "sell", "date": date, "price": round(price, 2),
                    "profit": round(profit, 2), "profit_pct": round((exit_price - entry_price) / entry_price * 100, 2)
                })

        # --- Final Valuation ---
        final_value = capital if position == 0 else position * df.iloc[-1]['Close']
        total_profit = final_value - initial_capital

        # --- Trade Metrics ---
        sell_trades = [t for t in trades if t.get("type") == "sell"]
        win_trades = [t for t in sell_trades if t["profit"] > 0]
        lose_trades = [t for t in sell_trades if t["profit"] <= 0]
        total_closed = len(sell_trades)
        win_rate = (len(win_trades) / total_closed * 100) if total_closed > 0 else 0

        gross_profit = sum(t["profit"] for t in win_trades)
        gross_loss = abs(sum(t["profit"] for t in lose_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        avg_win = (gross_profit / len(win_trades)) if win_trades else 0
        avg_loss = (gross_loss / len(lose_trades)) if lose_trades else 0

        # --- Advanced Metrics ---
        equity_values = [e["equity"] for e in equity_curve]

        # Sharpe Ratio (annualized, risk-free rate = 6% for Indonesia)
        if len(equity_values) > 1:
            returns = pd.Series(equity_values).pct_change().dropna()
            mean_return = returns.mean()
            std_return = returns.std()
            risk_free_daily = 0.06 / 252
            sharpe_ratio = ((mean_return - risk_free_daily) / std_return * math.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # Max Drawdown
        peak = equity_values[0]
        max_drawdown = 0
        max_drawdown_pct = 0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd
                max_drawdown = peak - eq

        # Calmar Ratio (annualized return / max drawdown)
        years = len(df) / 252
        annual_return_pct = ((final_value / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        calmar_ratio = (annual_return_pct / max_drawdown_pct) if max_drawdown_pct > 0 else 0

        # Sample equity curve (monthly) to keep response size small
        equity_sampled = equity_curve[::21]  # ~monthly
        if equity_curve and equity_curve[-1] not in equity_sampled:
            equity_sampled.append(equity_curve[-1])

        result = {
            "symbol": symbol,
            "strategy": strategy,
            "period": f"{len(df)} bars (~{years:.1f} years)",
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "profit_loss": round(total_profit, 2),
            "profit_pct": round(total_profit / initial_capital * 100, 2),
            "annual_return_pct": round(annual_return_pct, 2),
            "trades_count": len(trades),
            "closed_trades": total_closed,
            "win_rate": round(win_rate, 2),
            "metrics": {
                "sharpe_ratio": round(sharpe_ratio, 3),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "max_drawdown_value": round(max_drawdown, 2),
                "calmar_ratio": round(calmar_ratio, 3),
                "profit_factor": round(profit_factor, 3) if profit_factor != float('inf') else "Infinity",
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
            },
            "equity_curve": equity_sampled,
            "recent_trades": trades[-10:],  # Last 10 trades
        }

        log.info(f"Backtest done: {symbol}/{strategy} → {win_rate:.0f}% WR, Sharpe {sharpe_ratio:.2f}")
        return result

    except Exception as e:
        log.error(f"Backtest failed for {symbol}/{strategy}: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python backtest.py <SYMBOL> <STRATEGY>")
        sys.exit(1)

    result = run_backtest(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
