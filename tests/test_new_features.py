"""Tests for the 5 new CuanBot features with mocked AI/external calls."""

import json


# --- Chart Vision ---
class TestChartVision:
    def test_chart_vision_rejects_non_image(self, client):
        response = client.post(
            "/api/chart-vision",
            files={"file": ("test.txt", b"not an image", "text/plain")}
        )
        assert response.status_code == 400

    def test_chart_vision_accepts_image(self, client, api_mod):
        orig = api_mod.analyze_chart
        api_mod.analyze_chart = lambda img: {
            "patterns": [{"name": "Triangle", "confidence": "high"}],
            "trend": "Bullish",
            "verdict": "Breakout Potential",
        }
        try:
            png_bytes = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
                b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
                b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            response = client.post(
                "/api/chart-vision",
                files={"file": ("chart.png", png_bytes, "image/png")}
            )
            assert response.status_code == 200
            data = response.json()
            assert "patterns" in data
            assert data["verdict"] == "Breakout Potential"
        finally:
            api_mod.analyze_chart = orig


# --- Financial Report ---
class TestFinancialReport:
    def test_report_rejects_non_pdf(self, client):
        response = client.post(
            "/api/report",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        assert response.status_code == 400

    def test_report_processes_pdf(self, client, api_mod):
        orig = api_mod.analyze_report
        api_mod.analyze_report = lambda pdf: {
            "company": "Test Corp",
            "period": "2024",
            "metrics": {"revenue": {"value": 50000000000000, "unit": "IDR"}},
            "verdict": "Healthy",
            "analysis": "Keuangan sehat.",
            "pages_extracted": 3,
        }
        try:
            response = client.post(
                "/api/report",
                files={"file": ("lapkeu.pdf", b"%PDF-1.4 content", "application/pdf")}
            )
            assert response.status_code == 200
            assert response.json()["verdict"] == "Healthy"
        finally:
            api_mod.analyze_report = orig


# --- Macro Sentiment ---
class TestMacroSentiment:
    def test_macro_returns_data(self, client, api_mod):
        orig = api_mod.analyze_macro
        api_mod.analyze_macro = lambda: {
            "macro_data": {"usd_idr": 15800, "ihsg": {"value": 7200}},
            "analysis": {"outlook": "Bullish", "confidence": "medium"}
        }
        try:
            response = client.get("/api/macro")
            assert response.status_code == 200
            data = response.json()
            assert "macro_data" in data
            assert "analysis" in data
        finally:
            api_mod.analyze_macro = orig


# --- Bandarilogi ---
class TestBandarilogi:
    def test_bandarilogi_returns_data(self, client, api_mod):
        orig = api_mod.analyze_bandarmology
        api_mod.analyze_bandarmology = lambda s: {
            "symbol": s,
            "bandar_status": "Accumulation (Akumulasi)",
            "signal": "Bandar sedang mengumpulkan.",
            "recent_days": [],
            "ai_analysis": {"verdict": "Accumulation"},
        }
        try:
            response = client.get("/api/bandarilogi/BBCA.JK")
            assert response.status_code == 200
            data = response.json()
            assert "bandar_status" in data
            assert "ai_analysis" in data
        finally:
            api_mod.analyze_bandarmology = orig


# --- Sentiment AI ---
class TestSentimentAI:
    def test_sentiment_returns_score(self, client, api_mod):
        orig = api_mod.analyze_sentiment
        api_mod.analyze_sentiment = lambda t: {
            "ticker": t,
            "overall_score": 70,
            "overall_sentiment": "Bullish",
            "summary": "Sentimen positif.",
            "news_count": 1,
        }
        try:
            response = client.get("/api/sentiment/BBCA.JK")
            assert response.status_code == 200
            data = response.json()
            assert "overall_score" in data
            assert "overall_sentiment" in data
        finally:
            api_mod.analyze_sentiment = orig


# --- Root endpoint ---
class TestRootUpdated:
    def test_root_has_new_endpoints(self, client):
        response = client.get("/")
        data = response.json()
        endpoints = data["endpoints"]
        assert "/api/chart-vision" in endpoints
        assert "/api/report" in endpoints
        assert "/api/macro" in endpoints
        assert "/api/bandarilogi/{symbol}" in endpoints
        assert "/api/sentiment/{ticker}" in endpoints
        assert "/api/ai-advisor/{symbol}" in endpoints
