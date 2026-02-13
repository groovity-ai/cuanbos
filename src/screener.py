import sys
import json
import concurrent.futures
from market_data import get_stock_data, get_crypto_data
from tech_analysis import analyze_market_data

# List of stocks to screen (Example: LQ45 subset)
LQ45_STOCKS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", 
    "UNTR.JK", "GOTO.JK", "ADRO.JK", "PTBA.JK", "ANTM.JK", "PGAS.JK",
    "UNVR.JK", "ICBP.JK", "INDF.JK", "KLBF.JK", "BRPT.JK", "AKRA.JK"
]

def screen_stock(symbol):
    try:
        data = get_stock_data(symbol)
        if "error" in data:
            return None
        
        analysis = analyze_market_data(data)
        if "error" in analysis:
            return None
            
        return {
            "symbol": symbol,
            "price": analysis["price"],
            "rsi": analysis["momentum"]["rsi"],
            "trend": analysis["trend"]["status"],
            "pe": data["fundamentals"].get("pe_ratio"),
            "verdict": analysis["verdict"]
        }
    except Exception as e:
        return None

def main():
    filter_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    results = []
    print(f"🔍 Screening {len(LQ45_STOCKS)} stocks... (This may take a moment)")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(screen_stock, symbol): symbol for symbol in LQ45_STOCKS}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    # Filter results
    filtered = []
    if filter_type == "oversold":
        filtered = [r for r in results if r["rsi"] < 35]
    elif filter_type == "bullish":
        filtered = [r for r in results if "Bullish" in r["trend"]]
    elif filter_type == "cheap": # PE < 15
        filtered = [r for r in results if r["pe"] is not None and r["pe"] < 15 and r["pe"] > 0]
    else:
        filtered = results
        
    # Sort by RSI ascending (Most oversold first)
    filtered.sort(key=lambda x: x["rsi"])
    
    print(json.dumps(filtered, indent=2))

if __name__ == "__main__":
    main()
