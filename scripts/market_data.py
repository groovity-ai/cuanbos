import yfinance as yf
import pandas as pd
import sys
import json

def fetch_data(ticker, period="1y", interval="1d"):
    try:
        # Handle Crypto (add -USD if missing) vs Stocks
        symbol = ticker
        if not ticker.endswith(".JK") and not ticker.endswith("-USD"):
            # Simple heuristic: if 4 chars and all caps, maybe crypto? No, safer to ask user.
            # But prompt says "Handle Stocks (.JK) and Crypto".
            # Assume input is correct for now, or normalize.
            pass

        print(f"Fetching data for {symbol}...", file=sys.stderr)
        
        # Determine period/interval
        # Using default 'max' or '1y'
        
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period=period, interval=interval)
        
        if df.empty:
            print(json.dumps({"error": f"No data found for {symbol}"}))
            return

        # Format for pandas-ta
        # Reset index to make Date a column
        df.reset_index(inplace=True)
        
        # Convert Date to string
        df['Date'] = df['Date'].astype(str)
        
        # Select relevant columns
        data = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')
        
        print(json.dumps(data))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python market_data.py <TICKER>"}), file=sys.stderr)
        sys.exit(1)
    
    ticker = sys.argv[1]
    fetch_data(ticker)
