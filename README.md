# CuanBot 💹

AI-Powered Financial Analyst Engine for Indonesian stocks & crypto.

## Features

### Core Analysis
- **Technical Analysis** — RSI, MACD, MA crossover, Bollinger Bands, gorengan detection
- **Sentiment AI** — News sentiment scoring (-100 to +100) from Google News + CNBC Indonesia
- **Bandarilogi** — Foreign flow tracking via MFI, OBV, volume ratio
- **Macro Sentiment** — USD/IDR, IHSG, BI rate, bonds, VIX, DXY, oil + AI outlook
- **AI Advisor** — Unified verdict combining all modules + AI memory from past analyses

### Advanced Tools
- **Chart Vision** — Upload chart screenshot → Gemini Vision AI pattern detection
- **Financial Report** — Upload PDF laporan keuangan → AI analysis
- **Backtesting** — 3 strategies (RSI oversold, MA crossover, MACD reversal) with Sharpe ratio, max drawdown, equity curve
- **LQ45 Screener** — 45 stocks scored 0-100, sector grouping, filters
- **Portfolio & Risk** — CRUD portfolio positions, SL/TP monitoring

### Data Intelligence (v3.0)
- **Historical Storage** — JSONB snapshots of every analysis
- **Multi-Source Data** — CNBC Indonesia, bond yields, DXY, VIX, oil, BI rate
- **AI Memory** — LLM remembers past analyses & learns from user feedback
- **Feedback Loop** — 👍/👎 rating → accuracy tracking → injected into prompts

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API | FastAPI (async) + Uvicorn |
| Database | PostgreSQL (JSONB) |
| Cache | Redis 7 |
| AI/LLM | OpenClaw (Gemini 2.0 Flash) |
| Vision | Gemini Vision API |
| Data | yfinance, ccxt, pandas-ta |
| Testing | pytest (44 tests) |
| Infra | Docker Compose |

## Quick Start

```bash
# Clone & run
docker compose up -d

# Health check
curl http://localhost:8000/health

# Quick analysis
curl http://localhost:8000/api/ai-advisor/BBCA.JK
```

## API Endpoints (18 total)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ai-advisor/{symbol}` | GET | Full analysis + AI memory |
| `/api/analyze/{type}/{symbol}` | GET | Technical analysis |
| `/api/news/{ticker}` | GET | News (Google + CNBC) |
| `/api/sentiment/{ticker}` | GET | Sentiment AI scoring |
| `/api/bandarilogi/{symbol}` | GET | Foreign flow |
| `/api/macro` | GET | Macro economy (multi-source) |
| `/api/data-sources/{symbol}` | GET | Multi-source aggregation |
| `/api/history/{symbol}/full` | GET | Analysis history (JSONB) |
| `/api/history/{symbol}/trend` | GET | RSI/price time-series |
| `/api/feedback` | POST | Submit 👍/👎 feedback |
| `/api/feedback/stats` | GET | Accuracy statistics |
| `/api/backtest/{symbol}/{strategy}` | GET | Strategy backtest |
| `/api/screener` | GET | LQ45 screener |
| `/api/chart-vision` | POST | Chart image analysis |
| `/api/report` | POST | PDF report analysis |
| `/api/portfolio` | GET/POST/DEL | Portfolio management |
| `/api/risk` | GET | SL/TP monitor |
| `/health` | GET | Health check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_USER` | `postgres` | DB username |
| `DB_PASSWORD` | `postgres` | DB password |
| `DB_NAME` | `cuanbot` | DB name |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `AI_API_URL` | — | OpenClaw API URL |
| `AI_API_KEY` | — | API key |
| `AI_MODEL` | `gemini-2.0-flash` | LLM model |
| `GEMINI_API_KEY` | — | For chart vision |

## Project Structure

```
cuanbos/
├── src/
│   ├── api.py              # FastAPI app (v3.0, 18 endpoints)
│   ├── market_data.py       # OHLCV data fetcher
│   ├── tech_analysis.py     # RSI, MACD, MA, gorengan
│   ├── ai_advisor.py        # Unified AI verdict + memory
│   ├── ai_memory.py         # Context builder from history
│   ├── ai_client.py         # OpenClaw LLM client
│   ├── sentiment_ai.py      # News sentiment scoring
│   ├── bandarilogi.py       # Foreign flow analysis
│   ├── macro_sentiment.py   # Macro economy analysis
│   ├── data_sources.py      # Multi-source aggregator
│   ├── news.py              # Google + CNBC news
│   ├── chart_vision.py      # Gemini Vision chart AI
│   ├── financial_report.py  # PDF report RAG
│   ├── backtest.py          # Strategy backtester
│   ├── screener.py          # LQ45 screener
│   ├── database.py          # PostgreSQL + connection pool
│   ├── cache.py             # Redis caching layer
│   ├── logger.py            # Structured logging (loguru)
│   └── risk_monitor.py      # SL/TP monitoring
├── tests/                   # 44 tests
├── init.sql                 # DB schema
├── Dockerfile
├── docker-compose.yml
├── AGENT_INSTRUCTIONS.md    # Agent integration guide
└── SOUL.md                  # Agent personality
```

## Testing

```bash
cd cuanbos && python -m pytest tests/ -v
# 44 passed ✅
```

---

*Cuan is King, but Data is God.* 💹
