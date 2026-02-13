"""
Shared test configuration — centralizes sys.modules mocking.
This conftest.py runs before any test file collection.
"""

import sys
import os
import unittest.mock as mock
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# --- Mock loguru BEFORE anything imports it ---
class _MockLogger:
    def info(self, *a, **kw): pass
    def debug(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def bind(self, **kw): return self
    def add(self, *a, **kw): return 0
    def remove(self, *a, **kw): pass

_mock_loguru = mock.MagicMock()
_mock_loguru.logger = _MockLogger()
sys.modules['loguru'] = _mock_loguru

_mock_logger_mod = mock.MagicMock()
_mock_logger_mod.get_logger = lambda name: _MockLogger()
sys.modules['logger'] = _mock_logger_mod

# --- Mock Redis / cache ---
_mock_redis = mock.MagicMock()
sys.modules['redis'] = _mock_redis

_mock_cache = mock.MagicMock()
_mock_cache.cached = lambda prefix, ttl=900: lambda f: f  # No-op decorator
_mock_cache.get_cache = lambda k: None
_mock_cache.set_cache = lambda k, v, ttl=900: None
_mock_cache.TTL_MARKET_DATA = 300
_mock_cache.TTL_ANALYSIS = 900
_mock_cache.TTL_NEWS = 1800
_mock_cache.TTL_LLM = 3600
_mock_cache.TTL_SCREENER = 600
sys.modules['cache'] = _mock_cache

# --- Mock external dependencies at sys.modules level ---

# psycopg2
_mock_psycopg2 = mock.MagicMock()
_mock_psycopg2.pool = mock.MagicMock()
sys.modules['psycopg2'] = _mock_psycopg2
sys.modules['psycopg2.extras'] = mock.MagicMock()
sys.modules['psycopg2.pool'] = _mock_psycopg2.pool

# database module — includes new history/feedback functions
_mock_db = mock.MagicMock()
_mock_db.get_portfolio.return_value = []
_mock_db.add_portfolio_position.return_value = {
    "id": 1, "symbol": "BBCA.JK", "asset_type": "stock",
    "entry_price": 9000, "qty": 100, "sl_pct": -5, "tp_pct": 10
}
_mock_db.delete_portfolio_position.return_value = True
_mock_db.save_analysis.return_value = True
_mock_db.get_latest_analysis.return_value = None
_mock_db.close_pool = lambda: None
# History functions
_mock_db.save_analysis_history.return_value = 42
_mock_db.get_analysis_history.return_value = [
    {"id": 1, "symbol": "BBCA.JK", "analysis_type": "ai_advisor",
     "analysis_data": {"ai_verdict": {"verdict": "BUY", "confidence": 75}},
     "created_at": "2025-01-01 12:00:00"},
]
_mock_db.get_analysis_trend.return_value = [
    {"analysis_date": "2025-01-01", "price": 9000, "rsi": 55, "trend_status": "Bullish", "verdict": "BUY"},
]
# Feedback functions
_mock_db.save_feedback.return_value = {
    "id": 1, "analysis_id": 42, "symbol": "BBCA.JK", "rating": 1,
    "comment": None, "created_at": "2025-01-01 12:00:00"
}
_mock_db.get_feedback_stats.return_value = {
    "total": 10, "positive": 8, "negative": 2, "avg_rating": 0.6, "accuracy_pct": 80.0
}
sys.modules['database'] = _mock_db

# ai_client
_mock_ai = mock.MagicMock()
_mock_ai.chat_completion.return_value = '{"test": true}'
_mock_ai.vision_completion.return_value = '{"test": true}'
sys.modules['ai_client'] = _mock_ai

# data_sources module
_mock_data_sources = mock.MagicMock()
_mock_data_sources.aggregate_all_sources.return_value = {
    "macro_indicators": {"source": "macro_indicators", "indicators": {"vix": {"value": 15}}},
    "bi_rate": {"source": "bi_rate", "bi7drr": 6.0},
    "cnbc_news": {"source": "cnbc_indonesia", "news": []},
    "_meta": {"sources_total": 3, "sources_ok": 3},
}
_mock_data_sources.fetch_cnbc_news.return_value = {"source": "cnbc_indonesia", "news": []}
_mock_data_sources.fetch_indonesia_macro.return_value = {"source": "macro_indicators", "indicators": {}}
_mock_data_sources.fetch_bi_rate.return_value = {"source": "bi_rate", "bi7drr": 6.0}
sys.modules['data_sources'] = _mock_data_sources

# ai_memory module
_mock_ai_memory = mock.MagicMock()
_mock_ai_memory.format_memory_prompt.return_value = None
_mock_ai_memory.build_memory_context.return_value = None
_mock_ai_memory.build_feedback_context.return_value = None
sys.modules['ai_memory'] = _mock_ai_memory

# Clean up old module refs to force fresh imports
for mod_name in ['api', 'market_data', 'tech_analysis', 'news', 'backtest',
                 'screener', 'risk_monitor', 'portfolio',
                 'chart_vision', 'financial_report', 'macro_sentiment',
                 'bandarilogi', 'sentiment_ai', 'ai_advisor']:
    sys.modules.pop(mod_name, None)

# Import api once to share across all tests
from fastapi.testclient import TestClient
import api as _shared_api

_shared_client = TestClient(_shared_api.app)


@pytest.fixture
def client():
    return _shared_client


@pytest.fixture
def api_mod():
    return _shared_api
