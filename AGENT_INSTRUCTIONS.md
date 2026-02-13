# CuanBot Agent Instructions 🤖💸

This file contains the "Mental Tools" for CuanBot Agent.
Use these commands to access the Python backend engine inside Docker.

## 1. Analisa Saham & Crypto (Wajib sebelum jawab user)
Gunakan command ini untuk mendapatkan data harga + analisa teknikal otomatis.

**Command:**
```bash
# Format: <type: stock|crypto> <ticker>
# Contoh Saham (BBCA, ANTM):
docker exec cuanbot-engine python src/market_data.py stock BBCA.JK | docker exec -i cuanbot-engine python src/tech_analysis.py

# Contoh Crypto (BTC-USD, ETH-USD):
docker exec cuanbot-engine python src/market_data.py crypto BTC-USD | docker exec -i cuanbot-engine python src/tech_analysis.py
```

**Output (JSON):**
- `market_data`: Harga OHLCV, Fundamental (PE, PBV), Market Cap.
- `analysis`: 
  - Trend (Bullish/Bearish/Sideways)
  - Momentum (RSI Oversold/Overbought, MACD)
  - Volatility (Bollinger Bands)
  - Gorengan Score (Volume Spike, Anomaly)
  - Verdict (BUY/SELL/HOLD/AVOID)

**Cara Pakai:**
1. Jalankan command di atas.
2. Baca JSON output-nya.
3. Rangkum hasilnya ke bahasa manusia yang santai & "Cuan-able".
   - Jika Verdict "BUY", kasih semangat.
   - Jika Verdict "AVOID", peringatkan resiko gorengan.

## 2. Cek Berita & Sentimen (WAJIB BUAT KONFIRMASI)
Jangan cuma percaya teknikal. Cek dulu ada berita apa yang bisa mempengaruhi harga besok.

**Command:**
```bash
# Format: python src/news.py <ticker>
docker exec cuanbot-engine python src/news.py BBCA.JK
```

**Output (JSON):**
- List 5 berita terbaru (Judul, Link, Tanggal).
- Gunakan "Otak AI" lu untuk menentukan sentimen berita ini: Positif (Bullish) atau Negatif (Bearish)?
- Gabungkan sentimen ini dengan hasil teknikal di atas.

## 3. Backtesting Strategi (Validasi Masa Lalu)
Gunakan ini jika user minta bukti ("Emang strategi ini ampuh?").

**Command:**
```bash
# Strategi: rsi_oversold, ma_crossover, macd_reversal
# Format: python src/backtest.py <ticker> <strategy>
docker exec cuanbot-engine python src/backtest.py BBCA.JK rsi_oversold
```

**Output:**
- Win Rate, Total Profit, Max Drawdown, Jumlah Trade.
- Gunakan data ini untuk meyakinkan user (Data Driven).

## 4. Risk Monitor (Cek Portofolio)
Cek apakah ada saham yang kena Stop Loss atau Take Profit.

**Command:**
```bash
docker exec cuanbot-engine python src/risk_monitor.py
```

## 5. Screener (Cari Saham Potensial)
Cari saham yang lagi diskon atau lagi rame (Volume Spike).

**Command:**
```bash
# Cari yang RSI < 30 (Oversold)
docker exec cuanbot-engine python src/screener.py --rsi 30 --mode oversold

# Cari Gorengan (Volume Spike > 5x)
docker exec cuanbot-engine python src/screener.py --volume_spike 5
```

---
**PENTING:**
- Backend ada di Docker Container `cuanbot-engine`.
- File script ada di folder `/app/src` di dalam container.
- Agent harus punya akses `docker exec` untuk menjalankan tools ini.
