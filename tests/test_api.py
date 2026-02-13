"""Tests for CuanBot API routes (v3.0 — Data Intelligence)."""

import json


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "3.0.0"


class TestRootEndpoint:
    def test_root_returns_endpoints(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert data["name"] == "CuanBot API"
        assert data["version"] == "3.0.0"
        assert "/api/ai-advisor/{symbol}" in data["endpoints"]
        # New v3 endpoints
        assert "/api/history/{symbol}/full" in data["endpoints"]
        assert "/api/history/{symbol}/trend" in data["endpoints"]
        assert "/api/feedback" in data["endpoints"]
        assert "/api/data-sources/{symbol}" in data["endpoints"]


class TestAnalyzeEndpoint:
    def test_analyze_stock(self, client, api_mod):
        orig = {
            'get_stock_data': api_mod.get_stock_data,
            'analyze_market_data': api_mod.analyze_market_data,
            'save_analysis': api_mod.save_analysis,
            'save_analysis_history': api_mod.save_analysis_history,
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
        api_mod.save_analysis_history = lambda *a, **kw: 42
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
        api_mod.fetch_news = lambda t, l=5: {"ticker": t, "count": 1, "sources": ["Google News", "CNBC Indonesia"], "news": [{"title": "Test"}]}
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
            "has_memory": False,
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
            assert "has_memory" in data
        finally:
            api_mod.get_ai_advice = orig


# ========== NEW v3.0 TESTS ==========

class TestHistoryFullEndpoint:
    def test_history_full_returns_list(self, client, api_mod):
        orig = api_mod.get_analysis_history
        api_mod.get_analysis_history = lambda sym, typ=None, lim=10, off=0: [
            {"id": 1, "symbol": sym, "analysis_type": "ai_advisor",
             "analysis_data": {"ai_verdict": {"verdict": "BUY"}},
             "created_at": "2025-01-01 12:00:00"},
        ]
        try:
            response = client.get("/api/history/BBCA.JK/full")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BBCA.JK"
            assert "history" in data
            assert len(data["history"]) == 1
            assert data["history"][0]["analysis_type"] == "ai_advisor"
        finally:
            api_mod.get_analysis_history = orig

    def test_history_full_with_type_filter(self, client, api_mod):
        orig = api_mod.get_analysis_history
        api_mod.get_analysis_history = lambda sym, typ=None, lim=10, off=0: [
            {"id": 2, "symbol": sym, "analysis_type": "sentiment",
             "analysis_data": {"overall_score": 65}, "created_at": "2025-01-02"},
        ] if typ == "sentiment" else []
        try:
            response = client.get("/api/history/BBCA.JK/full?type=sentiment")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
        finally:
            api_mod.get_analysis_history = orig


class TestHistoryTrendEndpoint:
    def test_trend_returns_time_series(self, client, api_mod):
        orig = api_mod.get_analysis_trend
        api_mod.get_analysis_trend = lambda sym, days=30: [
            {"analysis_date": "2025-01-01", "price": 9000, "rsi": 55, "trend_status": "Bullish", "verdict": "BUY"},
            {"analysis_date": "2025-01-02", "price": 9100, "rsi": 58, "trend_status": "Bullish", "verdict": "BUY"},
        ]
        try:
            response = client.get("/api/history/BBCA.JK/trend?days=14")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BBCA.JK"
            assert data["data_points"] == 2
            assert "trend" in data
        finally:
            api_mod.get_analysis_trend = orig


class TestFeedbackEndpoint:
    def test_submit_positive_feedback(self, client, api_mod):
        orig = api_mod.save_feedback
        api_mod.save_feedback = lambda aid, sym, r, c=None: {
            "id": 1, "analysis_id": aid, "symbol": sym, "rating": r,
            "comment": c, "created_at": "2025-01-01 12:00:00"
        }
        try:
            response = client.post("/api/feedback", json={
                "analysis_id": 42, "symbol": "BBCA.JK", "rating": 1
            })
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "saved"
            assert data["feedback"]["rating"] == 1
        finally:
            api_mod.save_feedback = orig

    def test_invalid_rating_returns_400(self, client):
        response = client.post("/api/feedback", json={
            "analysis_id": 1, "symbol": "TEST", "rating": 5
        })
        assert response.status_code == 400


class TestFeedbackStatsEndpoint:
    def test_stats_returns_accuracy(self, client, api_mod):
        orig = api_mod.get_feedback_stats
        api_mod.get_feedback_stats = lambda s=None: {
            "total": 10, "positive": 8, "negative": 2, "accuracy_pct": 80.0
        }
        try:
            response = client.get("/api/feedback/stats?symbol=BBCA.JK")
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert data["stats"]["accuracy_pct"] == 80.0
        finally:
            api_mod.get_feedback_stats = orig


class TestDataSourcesEndpoint:
    def test_data_sources_returns_aggregated(self, client, api_mod):
        orig = api_mod.aggregate_all_sources
        api_mod.aggregate_all_sources = lambda t: {
            "macro_indicators": {"source": "macro_indicators", "indicators": {"vix": {"value": 15}}},
            "bi_rate": {"source": "bi_rate", "bi7drr": 6.0},
            "cnbc_news": {"source": "cnbc_indonesia", "news": []},
            "_meta": {"sources_total": 3, "sources_ok": 3},
        }
        try:
            response = client.get("/api/data-sources/BBCA.JK")
            assert response.status_code == 200
            data = response.json()
            assert "macro_indicators" in data
            assert "bi_rate" in data
            assert "_meta" in data
            assert data["_meta"]["sources_ok"] == 3
        finally:
            api_mod.aggregate_all_sources = orig
