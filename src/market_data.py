import yfinance as yf
import ccxt
import pandas as pd
import json
import sys
from datetime import datetime, timedelta

def get_stock_data(symbol, period="1y", interval="1d"):
    """
    Fetch stock data from Yahoo Finance.
    Symbol for Indo stocks: 'BBCA.JK'
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return {"error": f"No data found for symbol {symbol}"}
        
        # Reset index to make Date a column
        df.reset_index(inplace=True)
        
        # Format Date
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        
        # Get info for fundamentals
        info = ticker.info
        
        data = {
            "symbol": symbol,
            "type": "stock",
            "fundamentals": {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "eps": info.get("trailingEps"),
                "volume_avg": info.get("averageVolume"),
                "currency": info.get("currency"),
                "sector": info.get("sector")
            },
            "ohlcv": df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient='records')
        }
        return data
    except Exception as e:
        return {"error": str(e)}

def get_crypto_data(symbol, timeframe="1d", limit=365):
    """
    Fetch crypto data from CCXT (default: Binance).
    Symbol: 'BTC/USDT'
    """
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Convert to DataFrame for easier handling if needed, or just format list
        # CCXT returns: [timestamp, open, high, low, close, volume]
        formatted_data = []
        for candle in ohlcv:
            formatted_data.append({
                "Date": datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d'),
                "Open": candle[1],
                "High": candle[2],
                "Low": candle[3],
                "Close": candle[4],
                "Volume": candle[5]
            })
            
        data = {
            "symbol": symbol,
            "type": "crypto",
            "exchange": "binance",
            "ohlcv": formatted_data
        }
        return data
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python market_data.py <type:stock|crypto> <symbol>"}))
        sys.exit(1)
        
    asset_type = sys.argv[1]
    symbol = sys.argv[2]
    
    if asset_type == "stock":
        print(json.dumps(get_stock_data(symbol)))
    elif asset_type == "crypto":
        print(json.dumps(get_crypto_data(symbol)))
    else:
        print(json.dumps({"error": "Invalid type. Use 'stock' or 'crypto'."}))
