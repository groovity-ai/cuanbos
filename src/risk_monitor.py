import sys
import json
import yfinance as yf
from datetime import datetime
from database import get_portfolio

def monitor_risk():
    """Check portfolio positions against SL/TP thresholds using real DB data."""
    portfolio = get_portfolio()
    
    if not portfolio:
        print(json.dumps({"alerts": [], "message": "No positions in portfolio"}))
        return
    
    alerts = []
    summary = []
    
    for pos in portfolio:
        symbol = pos['symbol']
        try:
            ticker = yf.Ticker(symbol)
            try:
                current_price = ticker.fast_info['last_price']
            except Exception:
                hist = ticker.history(period="1d")
                if hist.empty:
                    continue
                current_price = hist['Close'].iloc[-1]
            
            entry = float(pos['entry_price'])
            qty = float(pos['qty'])
            sl_pct = float(pos['sl_pct'])
            tp_pct = float(pos['tp_pct'])
            pnl_pct = (current_price - entry) / entry * 100
            pnl_val = (current_price - entry) * qty
            
            status = "HOLD"
            action = "NONE"
            
            if pnl_pct <= sl_pct:
                status = "STOP_LOSS"
                action = "SELL_IMMEDIATELY"
            elif pnl_pct >= tp_pct:
                status = "TAKE_PROFIT"
                action = "SELL_PROFIT"
            
            position_info = {
                "id": pos['id'],
                "symbol": symbol,
                "entry_price": entry,
                "current_price": current_price,
                "qty": qty,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_val": round(pnl_val, 2),
                "status": status,
                "action": action,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "timestamp": datetime.now().isoformat()
            }
            
            if status != "HOLD":
                alerts.append(position_info)
            summary.append(position_info)
            
        except Exception as e:
            print(f"Error checking {symbol}: {e}", file=sys.stderr)
    
    output = {
        "alerts": alerts,
        "summary": summary,
        "total_positions": len(portfolio),
        "alert_count": len(alerts)
    }
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    monitor_risk()
