import pandas as pd
import pandas_ta as ta
import json
import sys
from database import save_analysis # Import DB saver

def analyze_market_data(data):
    """
    Analyze market data (OHLCV) using pandas-ta.
    Input: JSON object with 'ohlcv' list.
    Output: Analysis summary (Trend, Momentum, Volatility, Signals).
    """
    try:
        if "ohlcv" not in data or not data["ohlcv"]:
            return {"error": "No OHLCV data provided"}

        df = pd.DataFrame(data["ohlcv"])
        # Ensure correct types
        df['Close'] = pd.to_numeric(df['Close'])
        df['High'] = pd.to_numeric(df['High'])
        df['Low'] = pd.to_numeric(df['Low'])
        df['Volume'] = pd.to_numeric(df['Volume'])
        
        # --- 1. Trend Analysis ---
        # Moving Averages
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        
        current_price = df['Close'].iloc[-1]
        ma50 = df['SMA_50'].iloc[-1]
        ma200 = df['SMA_200'].iloc[-1]
        
        trend = "Sideways"
        if current_price > ma50 and current_price > ma200:
            trend = "Bullish (Strong Uptrend)"
        elif current_price < ma50 and current_price < ma200:
            trend = "Bearish (Strong Downtrend)"
        elif current_price > ma50:
             trend = "Bullish (Short-term)"
        elif current_price < ma50:
             trend = "Bearish (Short-term)"

        # Golden Cross / Death Cross
        # Check if cross happened recently (last 3 days)
        golden_cross = False
        death_cross = False
        
        if len(df) > 5:
            prev_ma50 = df['SMA_50'].iloc[-2]
            prev_ma200 = df['SMA_200'].iloc[-2]
            
            if prev_ma50 < prev_ma200 and ma50 > ma200:
                golden_cross = True
            elif prev_ma50 > prev_ma200 and ma50 < ma200:
                death_cross = True

        # --- 2. Momentum Analysis ---
        # RSI
        df.ta.rsi(length=14, append=True)
        rsi = df['RSI_14'].iloc[-1]
        
        momentum_signal = "Neutral"
        if rsi < 30:
            momentum_signal = "Oversold (Cheap)"
        elif rsi > 70:
            momentum_signal = "Overbought (Expensive)"

        # MACD
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        # macd returns a DataFrame with MACD, Histogram, Signal
        # Column names usually: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        macd_line = macd['MACD_12_26_9'].iloc[-1]
        macd_signal = macd['MACDs_12_26_9'].iloc[-1]
        
        macd_status = "Bullish" if macd_line > macd_signal else "Bearish"

        # --- 3. Volatility Analysis ---
        # Bollinger Bands
        bb = df.ta.bbands(length=20, std=2)
        # Columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        # Use iloc to be safe against column naming changes
        # bbands returns: Lower, Mid, Upper, Bandwidth, Percent (5 columns usually)
        # Let's inspect column names if debugging, but here we assume order or search
        
        # Safe retrieval by suffix if specific names fail, or just use what we know from pandas-ta docs
        # Default: BBL, BBM, BBU, BBB, BBP
        
        if bb is not None and not bb.empty:
            # Try specific columns first, else fallback by index
            # Upper is usually 2nd index (0=Lower, 1=Mid, 2=Upper) in some versions, or named explicitly
            # Let's try to find column ending with BBU_...
            bbu_col = [c for c in bb.columns if c.startswith('BBU')][0]
            bbl_col = [c for c in bb.columns if c.startswith('BBL')][0]
            
            bb_upper = bb[bbu_col].iloc[-1]
            bb_lower = bb[bbl_col].iloc[-1]
        else:
            bb_upper = 0
            bb_lower = 0
        
        volatility_status = "Normal"
        if current_price >= bb_upper:
            volatility_status = "High (Near Upper Band)"
        elif current_price <= bb_lower:
            volatility_status = "Low (Near Lower Band)"

        # --- 4. Gorengan Detector (Anomaly Detection) ---
        # Volume Spike
        avg_volume_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        
        is_volume_spike = volume_ratio > 5.0 # 5x average volume
        
        # Price Volatility (Standard Deviation of returns)
        # Daily return
        df['Return'] = df['Close'].pct_change()
        volatility_14d = df['Return'].rolling(window=14).std().iloc[-1]
        
        is_high_volatility = volatility_14d > 0.05 # >5% daily deviation is huge for stocks
        
        gorengan_score = 0
        gorengan_flags = []
        if is_volume_spike: 
            gorengan_score += 1
            gorengan_flags.append(f"Volume Spike ({volume_ratio:.1f}x avg)")
        if is_high_volatility: 
            gorengan_score += 1
            gorengan_flags.append(f"High Volatility ({volatility_14d*100:.1f}%)")
        
        # Fundamental check (if available)
        fundamental_score = 0
        fundamental_flags = []
        
        if "fundamentals" in data and data["fundamentals"]:
            fund = data["fundamentals"]
            pe = fund.get("pe_ratio")
            pb = fund.get("pb_ratio")
            
            if pe is not None:
                if pe < 0: 
                     gorengan_score += 1
                     gorengan_flags.append("Negative PE (Losing Money)")
                     fundamental_flags.append(f"Bad: PE Ratio {pe:.2f} (Negative)")
                elif pe < 15:
                    fundamental_score += 1
                    fundamental_flags.append(f"Good: PE Ratio {pe:.2f} (Cheap)")
                elif pe > 30:
                    fundamental_score -= 0.5
                    fundamental_flags.append(f"Expensive: PE Ratio {pe:.2f}")

            if pb is not None:
                if pb < 1:
                    fundamental_score += 1
                    fundamental_flags.append(f"Good: PBV {pb:.2f} (Undervalued)")
                elif pb > 5:
                    fundamental_flags.append(f"Expensive: PBV {pb:.2f}")
            
            # Small Cap check (e.g. < 1 Trillion IDR for Indo stocks)
            cap = fund.get("market_cap")
            if cap is not None and cap < 1_000_000_000_000 and data.get("type") == "stock":
                gorengan_score += 0.5
                gorengan_flags.append("Small Cap (<1T IDR)")

        is_gorengan = gorengan_score >= 2

        # --- Verdict ---
        verdict = "Hold / Neutral"
        if trend.startswith("Bullish") and momentum_signal == "Neutral":
            verdict = "Buy (Trend Following)"
        elif trend.startswith("Bullish") and momentum_signal == "Oversold":
            verdict = "Strong Buy (Dip)"
        elif momentum_signal == "Oversold" and fundamental_score > 0:
            verdict = "Buy (Value + Oversold)"
        elif trend.startswith("Bearish") or momentum_signal == "Overbought":
            verdict = "Sell / Wait"
            
        if is_gorengan:
            verdict = "AVOID (High Risk / Gorengan Indication)"

        # --- Summary ---
        analysis = {
            "price": current_price,
            "verdict": verdict,
            "trend": {
                "status": trend,
                "ma50": ma50,
                "ma200": ma200,
                "golden_cross": golden_cross,
                "death_cross": death_cross
            },
            "momentum": {
                "rsi": rsi,
                "status": momentum_signal,
                "macd": macd_status
            },
            "fundamental": {
                "score": fundamental_score,
                "flags": fundamental_flags
            },
            "volatility": {
                "status": volatility_status,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower
            },
            "anomalies": {
                "is_gorengan": is_gorengan,
                "score": gorengan_score,
                "flags": gorengan_flags,
                "volume_ratio": volume_ratio
            }
        }
        
        return analysis

    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

if __name__ == "__main__":
    # Read input from stdin (piped from market_data.py or file)
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"error": "No input data provided via stdin"}))
            sys.exit(1)
            
        market_data = json.loads(input_data)
        if "error" in market_data:
             print(json.dumps(market_data)) # Pass through error
             sys.exit(0)

        result = analyze_market_data(market_data)
        
        # Save to DB
        symbol = market_data.get("symbol")
        price = result.get("price")
        if symbol and price:
            save_analysis(symbol, price, result)
        
        # Combine market data with analysis
        output = {
            "market_data": market_data,
            "analysis": result
        }
        print(json.dumps(output, indent=2))
        
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
