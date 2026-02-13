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

# --- Mock external dependencies at sys.modules level ---

# psycopg2 (not available in test env)
sys.modules['psycopg2'] = mock.MagicMock()
sys.modules['psycopg2.extras'] = mock.MagicMock()

# database module
_mock_db = mock.MagicMock()
_mock_db.get_portfolio.return_value = []
_mock_db.add_portfolio_position.return_value = {
    "id": 1, "symbol": "BBCA.JK", "asset_type": "stock",
    "entry_price": 9000, "qty": 100, "sl_pct": -5, "tp_pct": 10
}
_mock_db.delete_portfolio_position.return_value = True
_mock_db.save_analysis.return_value = True
_mock_db.get_latest_analysis.return_value = None
sys.modules['database'] = _mock_db

# ai_client
_mock_ai = mock.MagicMock()
_mock_ai.chat_completion.return_value = '{"test": true}'
_mock_ai.vision_completion.return_value = '{"test": true}'
sys.modules['ai_client'] = _mock_ai

# Clean up old module refs to force fresh imports
for mod_name in ['api', 'market_data', 'tech_analysis', 'news', 'backtest',
                 'screener', 'risk_monitor', 'portfolio',
                 'chart_vision', 'financial_report', 'macro_sentiment',
                 'bandarilogi', 'sentiment_ai']:
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
