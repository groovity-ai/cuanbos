import pandas as pd
import pandas_ta as ta
import json
import sys

def analyze(data_json):
    try:
        df = pd.DataFrame(data_json)
        
        # Ensure we have OHLCV
        if df.empty:
            return {"error": "Empty data"}

        # Calculate Indicators
        # RSI 14
        df['RSI'] = df.ta.rsi(length=14)
        
        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        
        # MA 50 & 200
        df['MA50'] = df.ta.sma(length=50)
        df['MA200'] = df.ta.sma(length=200)

        # GORENGAN DETECTOR
        # Logic: Volume > 5x Average (20d) AND Price High Volatility
        df['Vol_Avg20'] = df.ta.sma(close='Volume', length=20)
        
        # Get latest candle
        latest = df.iloc[-1]
        
        is_gorengan = False
        gorengan_reason = []
        
        if latest['Volume'] > (latest['Vol_Avg20'] * 5):
            is_gorengan = True
            gorengan_reason.append("Volume spike > 5x Average")
            
        # Volatility check (ATR or just High/Low range)
        # Using simple High-Low range %
        daily_range_pct = (latest['High'] - latest['Low']) / latest['Low'] * 100
        if daily_range_pct > 10: # >10% daily swing
            is_gorengan = True
            gorengan_reason.append(f"High Volatility ({daily_range_pct:.2f}%)")

        result = {
            "ticker": "UNKNOWN", # Need to pass ticker too? Or just analysis.
            "latest_close": latest['Close'],
            "rsi": latest['RSI_14'] if 'RSI_14' in latest else latest.get('RSI'),
            "macd": latest.get('MACD_12_26_9'),
            "macd_signal": latest.get('MACDs_12_26_9'),
            "ma50": latest['MA50'],
            "ma200": latest['MA200'],
            "trend": "Bullish" if latest['Close'] > latest['MA50'] else "Bearish",
            "gorengan_alert": {
                "is_high_risk": is_gorengan,
                "reasons": gorengan_reason
            }
        }
        
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    # Read JSON from stdin
    input_data = sys.stdin.read()
    if not input_data:
        print(json.dumps({"error": "No input data provided"}))
        sys.exit(1)
        
    data = json.loads(input_data)
    analyze(data)
