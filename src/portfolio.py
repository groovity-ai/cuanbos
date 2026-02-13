import sys
import json
from market_data import get_stock_data, get_crypto_data
from tech_analysis import analyze_market_data

# Simple portfolio file (JSON)
PORTFOLIO_FILE = "/app/src/portfolio.json"

def load_portfolio():
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_portfolio(porto):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(porto, f, indent=2)

def add_position(symbol, type, buy_price, amount):
    porto = load_portfolio()
    porto.append({
        "symbol": symbol,
        "type": type,
        "buy_price": float(buy_price),
        "amount": float(amount)
    })
    save_portfolio(porto)
    return {"status": "added", "symbol": symbol}

def check_portfolio():
    porto = load_portfolio()
    report = []
    total_pnl = 0
    
    for pos in porto:
        if pos["type"] == "stock":
            data = get_stock_data(pos["symbol"])
        else:
            data = get_crypto_data(pos["symbol"])
            
        if "error" in data:
            continue
            
        current_price = data["ohlcv"][-1]["Close"]
        pnl_pct = ((current_price - pos["buy_price"]) / pos["buy_price"]) * 100
        pnl_val = (current_price - pos["buy_price"]) * pos["amount"]
        total_pnl += pnl_val
        
        # Simple analysis
        analysis = analyze_market_data(data)
        trend = analysis["trend"]["status"] if "trend" in analysis else "Unknown"
        
        report.append({
            "symbol": pos["symbol"],
            "buy": pos["buy_price"],
            "curr": current_price,
            "pnl_%": round(pnl_pct, 2),
            "pnl_val": round(pnl_val, 2),
            "trend": trend,
            "verdict": analysis.get("verdict", "Hold")
        })
        
    return {"portfolio": report, "total_pnl": round(total_pnl, 2)}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    
    if action == "add":
        # python portfolio.py add BBCA.JK stock 9000 100
        if len(sys.argv) < 6:
            print("Usage: add <symbol> <type> <price> <amount>")
        else:
            print(json.dumps(add_position(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])))
    else:
        print(json.dumps(check_portfolio(), indent=2))
