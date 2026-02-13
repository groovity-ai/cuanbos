"""
Bandarilogi / Foreign Flow Tracker
Track big money movement and accumulation/distribution patterns.
"""

import json
import yfinance as yf
import pandas as pd
from ai_client import chat_completion


def get_foreign_flow_data(symbol):
    """
    Analyze foreign flow / big money movement using volume and price analysis.
    Since IDX broker summary data isn't publicly available via API,
    we use volume-price analysis as a proxy for institutional activity.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3mo")

        if df.empty:
            return {"error": f"No data for {symbol}"}

        df = df.reset_index()

        # Volume-Price Analysis (proxy for institutional flow)
        # 1. Money Flow Index (MFI) - like RSI but volume-weighted
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']

        # Positive/Negative flow
        positive_flow = []
        negative_flow = []
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            else:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])

        # Calculate 14-day rolling
        pos_series = pd.Series([0] + positive_flow)
        neg_series = pd.Series([0] + negative_flow)
        pos_14 = pos_series.rolling(14).sum().iloc[-1]
        neg_14 = neg_series.rolling(14).sum().iloc[-1]

        mfi = 100 - (100 / (1 + pos_14 / neg_14)) if neg_14 > 0 else 100

        # 2. On-Balance Volume (OBV) trend
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])

        obv_series = pd.Series(obv)
        obv_trend = "Up" if obv_series.iloc[-1] > obv_series.iloc[-5] else "Down"

        # 3. Volume trend (institutional usually = high volume)
        avg_vol_20 = df['Volume'].rolling(20).mean().iloc[-1]
        current_vol = df['Volume'].iloc[-1]
        vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0

        # 4. Price trend
        price_5d_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-5]) / df['Close'].iloc[-5]) * 100
        price_20d_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) * 100

        # 5. Determine accumulation/distribution
        # Accumulation: Price down or flat + OBV up + High MFI = big money buying
        # Distribution: Price up + OBV down + Low MFI = big money selling
        if obv_trend == "Up" and mfi > 50 and price_5d_change < 2:
            bandar_status = "Accumulation (Akumulasi)"
            signal = "Bandar sedang mengumpulkan. Potensi naik."
        elif obv_trend == "Down" and mfi < 50 and price_5d_change > -2:
            bandar_status = "Distribution (Distribusi)"
            signal = "Bandar sedang buang barang. Hati-hati!"
        elif obv_trend == "Up" and price_5d_change > 0:
            bandar_status = "Markup"
            signal = "Volume mendukung kenaikan. Trend valid."
        elif obv_trend == "Down" and price_5d_change < 0:
            bandar_status = "Markdown"
            signal = "Tekanan jual besar. Hindari dulu."
        else:
            bandar_status = "Neutral"
            signal = "Belum ada sinyal jelas dari bandar."

        # Recent 5 days detail
        recent_days = []
        for i in range(-5, 0):
            idx = len(df) + i
            if idx >= 0:
                row = df.iloc[idx]
                day_flow = "Inflow" if row['Close'] > row['Open'] and vol_ratio > 1 else "Outflow" if row['Close'] < row['Open'] else "Neutral"
                recent_days.append({
                    "date": str(row['Date'].date()) if hasattr(row['Date'], 'date') else str(row['Date'])[:10],
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume']),
                    "flow": day_flow,
                })

        return {
            "symbol": symbol,
            "indicators": {
                "mfi_14": round(mfi, 2),
                "obv_trend": obv_trend,
                "volume_ratio": round(vol_ratio, 2),
                "price_5d_change": round(price_5d_change, 2),
                "price_20d_change": round(price_20d_change, 2),
            },
            "bandar_status": bandar_status,
            "signal": signal,
            "recent_days": recent_days,
        }

    except Exception as e:
        return {"error": f"Bandarilogi analysis failed: {str(e)}"}


def analyze_bandarmology(symbol):
    """
    Full bandarmology analysis with AI commentary.
    """
    data = get_foreign_flow_data(symbol)
    if "error" in data:
        return data

    # Get AI commentary
    messages = [
        {
            "role": "system",
            "content": """You are CuanBot Bandarmology Analyst. Analyze the money flow data.
Respond in VALID JSON:
{
    "verdict": "Accumulation / Distribution / Markup / Markdown / Neutral",
    "confidence": "high/medium/low",
    "explanation": "2-3 sentence explanation in Bahasa Indonesia (santai, gaya lo-gue)",
    "action": "Buy / Sell / Hold / Watch"
}"""
        },
        {"role": "user", "content": f"Bandarmology data for {symbol}:\n{json.dumps(data, indent=2)}"},
    ]

    try:
        response = chat_completion(messages)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        try:
            ai_analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            ai_analysis = {"verdict": data["bandar_status"], "raw_response": response}
    except Exception as e:
        ai_analysis = {"error": str(e)}

    data["ai_analysis"] = ai_analysis
    return data


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BBCA.JK"
    result = analyze_bandarmology(symbol)
    print(json.dumps(result, indent=2, default=str))
