import sys
import json
import pandas as pd
import yfinance as yf
import pandas_ta as ta

def run_backtest(symbol, strategy, initial_capital=10000000):
    try:
        # Fetch Data
        df = yf.Ticker(symbol).history(period="5y")
        if df.empty:
            return {"error": "No data"}
        
        # Calculate Indicators
        df['RSI'] = df.ta.rsi(length=14)
        df['MA50'] = df.ta.sma(length=50)
        df['MA200'] = df.ta.sma(length=200)
        
        # Simulation
        capital = initial_capital
        position = 0 # 0 = flat, >0 = shares
        entry_price = 0
        trades = []
        
        for i in range(len(df)):
            if i < 200: continue # Skip warmup
            
            row = df.iloc[i]
            prev = df.iloc[i-1]
            price = row['Close']
            date = str(row.name)
            
            signal = "hold"
            
            # Strategy Logic
            if strategy == "rsi_oversold":
                if position == 0 and prev['RSI'] < 30:
                    signal = "buy"
                elif position > 0 and prev['RSI'] > 70:
                    signal = "sell"
                    
            elif strategy == "ma_crossover":
                # Golden Cross / Death Cross
                if position == 0 and prev['MA50'] > prev['MA200'] and df.iloc[i-2]['MA50'] <= df.iloc[i-2]['MA200']:
                    signal = "buy"
                elif position > 0 and prev['MA50'] < prev['MA200']:
                    signal = "sell"
            
            # Execute
            if signal == "buy" and position == 0:
                position = capital / price
                entry_price = price
                capital = 0
                trades.append({"type": "buy", "date": date, "price": price})
                
            elif signal == "sell" and position > 0:
                exit_price = price
                profit = (exit_price - entry_price) * position
                capital = position * exit_price
                position = 0
                trades.append({"type": "sell", "date": date, "price": price, "profit": profit})

        # Final Valuation
        final_value = capital if position == 0 else position * df.iloc[-1]['Close']
        total_profit = final_value - initial_capital
        win_trades = len([t for t in trades if t.get('type') == 'sell' and t['profit'] > 0])
        total_closed = len([t for t in trades if t.get('type') == 'sell'])
        win_rate = (win_trades / total_closed * 100) if total_closed > 0 else 0
        
        result = {
            "symbol": symbol,
            "strategy": strategy,
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "profit_loss": round(total_profit, 2),
            "profit_pct": round(total_profit / initial_capital * 100, 2),
            "trades_count": len(trades),
            "win_rate": round(win_rate, 2)
        }
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python backtest.py <SYMBOL> <STRATEGY>")
        sys.exit(1)
        
    run_backtest(sys.argv[1], sys.argv[2])
