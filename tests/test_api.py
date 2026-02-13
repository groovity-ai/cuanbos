"""Tests for FastAPI API routes."""

import json


class TestRootEndpoint:
    def test_root_returns_endpoints(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert data["name"] == "CuanBot API"


class TestAnalyzeEndpoint:
    def test_analyze_stock(self, client, api_mod):
        """Test analyze endpoint."""
        orig = {
            'get_stock_data': api_mod.get_stock_data,
            'analyze_market_data': api_mod.analyze_market_data,
            'save_analysis': api_mod.save_analysis,
        }
        api_mod.get_stock_data = lambda s: {
            "symbol": "TEST", "type": "stock",
            "ohlcv": [{"Date": "2025-01-01", "Close": 100}]
        }
        api_mod.analyze_market_data = lambda d: {
            "price": 100, "verdict": "Hold",
            "trend": {"status": "Sideways"}, "momentum": {"rsi": 50}
        }
        api_mod.save_analysis = lambda *a, **kw: True
        try:
            response = client.get("/api/analyze/stock/TEST")
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert data["analysis"]["verdict"] == "Hold"
        finally:
            for k, v in orig.items():
                setattr(api_mod, k, v)

    def test_invalid_type_returns_400(self, client):
        response = client.get("/api/analyze/invalid/TEST")
        assert response.status_code == 400


class TestNewsEndpoint:
    def test_news_returns_data(self, client, api_mod):
        orig = api_mod.fetch_news
        api_mod.fetch_news = lambda t, l=5: {"ticker": t, "count": 1, "news": [{"title": "Test"}]}
        try:
            response = client.get("/api/news/BBCA.JK")
            assert response.status_code == 200
            assert "news" in response.json()
        finally:
            api_mod.fetch_news = orig


class TestBacktestEndpoint:
    def test_invalid_strategy_returns_400(self, client):
        response = client.get("/api/backtest/TEST/invalid_strategy")
        assert response.status_code == 400

    def test_valid_strategy(self, client, api_mod):
        orig = api_mod.run_backtest
        api_mod.run_backtest = lambda s, st: print(json.dumps({
            "symbol": s, "strategy": st, "win_rate": 60, "profit_pct": 15
        }))
        try:
            response = client.get("/api/backtest/TEST/rsi_oversold")
            assert response.status_code == 200
        finally:
            api_mod.run_backtest = orig


class TestPortfolioEndpoints:
    def test_get_portfolio(self, client):
        response = client.get("/api/portfolio")
        assert response.status_code == 200
        assert "positions" in response.json()

    def test_add_portfolio(self, client):
        response = client.post("/api/portfolio", json={
            "symbol": "BBCA.JK", "type": "stock", "buy_price": 9000, "amount": 100
        })
        assert response.status_code == 200
        assert response.json()["status"] == "added"

    def test_delete_portfolio(self, client):
        response = client.delete("/api/portfolio/1")
        assert response.status_code == 200


class TestRiskEndpoint:
    def test_risk_returns_data(self, client, api_mod):
        orig = api_mod.monitor_risk
        api_mod.monitor_risk = lambda: print(json.dumps({"alerts": [], "summary": []}))
        try:
            response = client.get("/api/risk")
            assert response.status_code == 200
        finally:
            api_mod.monitor_risk = orig
