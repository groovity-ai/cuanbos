"""Tests for CuanBot API routes (async version)."""

import json


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"


class TestRootEndpoint:
    def test_root_returns_endpoints(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert data["name"] == "CuanBot API"
        assert data["version"] == "2.0.0"
        assert "/api/ai-advisor/{symbol}" in data["endpoints"]


class TestAnalyzeEndpoint:
    def test_analyze_stock(self, client, api_mod):
        """Test analyze endpoint with direct attribute replacement."""
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

    def test_valid_strategy_returns_enhanced_metrics(self, client, api_mod):
        orig = api_mod.run_backtest
        api_mod.run_backtest = lambda s, st: {
            "symbol": s, "strategy": st,
            "initial_capital": 10000000,
            "final_value": 11500000,
            "profit_loss": 1500000,
            "profit_pct": 15.0,
            "annual_return_pct": 7.5,
            "trades_count": 10,
            "closed_trades": 5,
            "win_rate": 60.0,
            "metrics": {
                "sharpe_ratio": 1.2,
                "max_drawdown_pct": 8.5,
                "max_drawdown_value": 850000,
                "calmar_ratio": 0.88,
                "profit_factor": 2.1,
                "avg_win": 500000,
                "avg_loss": 200000,
            },
            "equity_curve": [{"date": "2024-01-01", "equity": 10000000}],
            "recent_trades": [],
        }
        try:
            response = client.get("/api/backtest/TEST/rsi_oversold")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "sharpe_ratio" in data["metrics"]
            assert "max_drawdown_pct" in data["metrics"]
            assert "calmar_ratio" in data["metrics"]
            assert "profit_factor" in data["metrics"]
            assert "equity_curve" in data
        finally:
            api_mod.run_backtest = orig


class TestScreenerEndpoint:
    def test_screener_returns_composite_scores(self, client, api_mod):
        orig = api_mod.run_screener
        api_mod.run_screener = lambda f="all", ms=0, s=None: {
            "count": 2,
            "total_screened": 45,
            "top_pick": {"symbol": "BBCA.JK", "composite_score": 85},
            "sectors": {"Financial Services": {"count": 1, "avg_score": 85}},
            "stocks": [
                {"symbol": "BBCA.JK", "composite_score": 85, "rsi": 32, "trend": "Bullish"},
                {"symbol": "BBRI.JK", "composite_score": 70, "rsi": 40, "trend": "Sideways"},
            ]
        }
        try:
            response = client.get("/api/screener?min_score=60")
            assert response.status_code == 200
            data = response.json()
            assert "total_screened" in data
            assert "sectors" in data
            assert "composite_score" in data["stocks"][0]
        finally:
            api_mod.run_screener = orig


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
        api_mod.monitor_risk = lambda: {"alerts": [], "summary": [], "total_positions": 0, "alert_count": 0}
        try:
            response = client.get("/api/risk")
            assert response.status_code == 200
            data = response.json()
            assert "alerts" in data
            assert "summary" in data
        finally:
            api_mod.monitor_risk = orig


class TestAIAdvisorEndpoint:
    def test_ai_advisor_returns_verdict(self, client, api_mod):
        orig = api_mod.get_ai_advice
        api_mod.get_ai_advice = lambda s: {
            "symbol": s,
            "ai_verdict": {
                "verdict": "BUY",
                "confidence": 75,
                "reasoning": "Teknikal dan sentimen positif",
                "key_factors": ["RSI oversold", "Bullish trend"],
                "risk_level": "Medium",
            },
            "data_sources": {
                "technical": {"price": 9500, "verdict": "Buy"},
                "bandarilogi": None,
                "sentiment": None,
                "macro": None,
            }
        }
        try:
            response = client.get("/api/ai-advisor/BBCA.JK")
            assert response.status_code == 200
            data = response.json()
            assert "ai_verdict" in data
            assert data["ai_verdict"]["verdict"] == "BUY"
            assert "confidence" in data["ai_verdict"]
            assert "data_sources" in data
        finally:
            api_mod.get_ai_advice = orig
