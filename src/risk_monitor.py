import sys
import json
import yfinance as yf

# Mock Database (In reality, fetch from Postgres)
PORTFOLIO = [
    {"symbol": "BBCA.JK", "entry_price": 9500, "qty": 100, "sl_pct": -5, "tp_pct": 10},
    {"symbol": "TLKM.JK", "entry_price": 4000, "qty": 500, "sl_pct": -3, "tp_pct": 8},
    {"symbol": "BTC-USD", "entry_price": 60000, "qty": 0.1, "sl_pct": -10, "tp_pct": 20}
]

def monitor_risk():
    alerts = []
    
    for pos in PORTFOLIO:
        symbol = pos['symbol']
        try:
            ticker = yf.Ticker(symbol)
            # Use 'regularMarketPrice' or fetch history for latest close
            # Using fast info if available, else history 1d
            try:
                current_price = ticker.fast_info['last_price']
            except:
                hist = ticker.history(period="1d")
                if hist.empty: continue
                current_price = hist['Close'].iloc[-1]
                
            entry = pos['entry_price']
            pnl_pct = (current_price - entry) / entry * 100
            
            status = "HOLD"
            action = "NONE"
            
            if pnl_pct <= pos['sl_pct']:
                status = "STOP_LOSS"
                action = "SELL_IMMEDIATELY"
            elif pnl_pct >= pos['tp_pct']:
                status = "TAKE_PROFIT"
                action = "SELL_PROFIT"
                
            if status != "HOLD":
                alert = {
                    "symbol": symbol,
                    "status": status,
                    "action": action,
                    "current_price": current_price,
                    "pnl_pct": round(pnl_pct, 2),
                    "timestamp": "now"
                }
                alerts.append(alert)
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}", file=sys.stderr)
            
    print(json.dumps({"alerts": alerts}, indent=2))

if __name__ == "__main__":
    monitor_risk()
