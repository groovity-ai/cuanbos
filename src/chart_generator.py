"""
Chart Visualization Generator 📊
Generates candlestick charts with technical indicators (RSI, MACD) as image files.
"""

import os
import io
import datetime
import pandas as pd
import mplfinance as mpf
from market_data import get_crypto_data as fetch_crypto_data, get_stock_data as fetch_stock_data
from tech_analysis import analyze_market_data
import pandas_ta as ta
from logger import get_logger

log = get_logger("chart_generator")

def generate_chart(ticker, market_type="crypto", days=60):
    """
    Fetch data, calculate indicators, and generate a PNG chart.
    Returns the raw PNG bytes.
    """
    try:
        # 1. Fetch Data
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        if market_type == "crypto":
            # For crypto, ccxt might need different timeframe handling, but let's try standard fetch
            # To be safe, we'll just fetch a bit more data
            res = fetch_crypto_data(ticker, timeframe='1d', limit=days+30)
            df = pd.DataFrame(res.get('ohlcv', []))
        else:
            res = fetch_stock_data(ticker, period="1y")
            df = pd.DataFrame(res.get('ohlcv', []))
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
            
        if df.empty:
            raise ValueError(f"No data found for {ticker}")

        # Ensure index is datetime for mplfinance
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

        # 2. Calculate Indicators
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df_ta = df
        
        # Trim to requested days to avoid squeezing the chart
        df_ta = df_ta.tail(days)

        # 3. Prepare Plots
        # Create additional plots for MACD and RSI
        addplots = []
        
        # Moving Averages (on main chart)
        if 'SMA_20' in df_ta.columns:
            addplots.append(mpf.make_addplot(df_ta['SMA_20'], color='orange', width=1.5))
        if 'SMA_50' in df_ta.columns:
            addplots.append(mpf.make_addplot(df_ta['SMA_50'], color='blue', width=1.5))
            
        # MACD (panel 1)
        if 'MACD_12_26_9' in df_ta.columns:
            addplots.append(mpf.make_addplot(df_ta['MACD_12_26_9'], panel=1, color='green', secondary_y=False))
            addplots.append(mpf.make_addplot(df_ta['MACDs_12_26_9'], panel=1, color='red', secondary_y=False))
            
            # MACD Histogram
            macd_hist = df_ta['MACD_12_26_9'] - df_ta['MACDs_12_26_9']
            colors = ['green' if val >= 0 else 'red' for val in macd_hist]
            addplots.append(mpf.make_addplot(macd_hist, type='bar', panel=1, color=colors, secondary_y=False))

        # RSI (panel 2)
        if 'RSI_14' in df_ta.columns:
            addplots.append(mpf.make_addplot(df_ta['RSI_14'], panel=2, color='purple', secondary_y=False))
            # RSI Overbought/Oversold lines
            addplots.append(mpf.make_addplot([70]*len(df_ta), panel=2, color='red', linestyle='--', width=1))
            addplots.append(mpf.make_addplot([30]*len(df_ta), panel=2, color='green', linestyle='--', width=1))

        # 4. Generate Image to Bytes
        buf = io.BytesIO()
        
        # Custom style for "CuanBot" dark mode
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', 
                               rc={'font.size': 8, 'axes.labelsize': 8})
        
        mpf.plot(df_ta, 
                 type='candle', 
                 volume=True, 
                 addplot=addplots,
                 style=s,
                 title=f"\n{ticker} - CuanBot Analysis",
                 ylabel='Price',
                 ylabel_lower='Volume',
                 figratio=(12, 8),
                 figscale=1.2,
                 panel_ratios=(4, 1, 1.5, 1.5), # Main, Volume, MACD, RSI
                 savefig=dict(fname=buf, format='png', bbox_inches='tight', pad_inches=0.1))
        
        buf.seek(0)
        return buf.read()
        
    except Exception as e:
        import traceback
        log.error(f"Failed to generate chart for {ticker}: {e}\n{traceback.format_exc()}")
        raise Exception(f"Failed to generate chart for {ticker}: {str(e)}")
