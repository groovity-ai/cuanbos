"""
Multi-source data aggregator for CuanBot.
Fetches data from CNBC Indonesia, Trading Economics, Bank Indonesia, Yahoo bonds.
All fetchers are cached and gracefully degrade on failure.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import yfinance as yf
from cache import cached, TTL_NEWS, TTL_MARKET_DATA
from logger import get_logger

log = get_logger("data_sources")


# ============================================================
# CNBC Indonesia RSS
# ============================================================

@cached("cnbc_news", ttl=TTL_NEWS)
def fetch_cnbc_news(ticker=None, limit=5):
    """
    Fetch financial news from CNBC Indonesia RSS.
    More targeted Indonesian market coverage than Google News.
    """
    try:
        feeds = [
            ("market", "https://www.cnbcindonesia.com/market/rss"),
            ("investment", "https://www.cnbcindonesia.com/investment/rss"),
        ]

        all_news = []
        for category, url in feeds:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 CuanBot/2.0'})
                with urllib.request.urlopen(req, timeout=8) as response:
                    xml_data = response.read()

                root = ET.fromstring(xml_data)
                for item in root.findall('.//item'):
                    if len(all_news) >= limit * 2:
                        break

                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    desc = item.find('description')

                    title_text = title.text if title is not None else ""
                    # If ticker specified, filter by relevance
                    if ticker:
                        clean_ticker = ticker.split('.')[0].upper()
                        if clean_ticker.lower() not in title_text.lower():
                            continue

                    all_news.append({
                        "source": f"CNBC Indonesia ({category})",
                        "title": title_text,
                        "link": link.text if link is not None else "",
                        "date": pub_date.text if pub_date is not None else "",
                        "snippet": _clean_html(desc.text[:200]) if desc is not None and desc.text else "",
                    })
            except Exception as e:
                log.warning(f"CNBC {category} feed failed: {e}")

        return {"source": "cnbc_indonesia", "count": len(all_news[:limit]), "news": all_news[:limit]}

    except Exception as e:
        log.error(f"CNBC Indonesia fetch failed: {e}")
        return {"source": "cnbc_indonesia", "error": str(e), "news": []}


def _clean_html(text):
    """Strip HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text).strip()


# ============================================================
# Trading Economics (key macro indicators via scraping)
# ============================================================

@cached("trading_economics", ttl=TTL_MARKET_DATA)
def fetch_indonesia_macro():
    """
    Fetch key Indonesia macro indicators from Yahoo Finance proxies.
    Uses yfinance tickers as reliable source for macro data.
    """
    try:
        indicators = {}

        # Indonesia 10Y Bond Yield
        try:
            bond_id = yf.Ticker("ID10Y.JK")
            hist = bond_id.history(period="5d")
            if not hist.empty:
                indicators["indonesia_10y_bond"] = {
                    "value": round(hist['Close'].iloc[-1], 2),
                    "unit": "%",
                    "description": "Indonesia 10Y Government Bond Yield"
                }
        except Exception:
            pass

        # US 10Y Bond Yield (for comparison)
        try:
            bond_us = yf.Ticker("^TNX")
            hist = bond_us.history(period="5d")
            if not hist.empty:
                indicators["us_10y_bond"] = {
                    "value": round(hist['Close'].iloc[-1], 2),
                    "unit": "%",
                    "description": "US 10Y Treasury Yield"
                }
        except Exception:
            pass

        # DXY (Dollar Index) — affects emerging markets
        try:
            dxy = yf.Ticker("DX-Y.NYB")
            hist = dxy.history(period="5d")
            if not hist.empty:
                indicators["dxy"] = {
                    "value": round(hist['Close'].iloc[-1], 2),
                    "description": "US Dollar Index"
                }
        except Exception:
            pass

        # VIX (Fear Index)
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="5d")
            if not hist.empty:
                val = round(hist['Close'].iloc[-1], 2)
                indicators["vix"] = {
                    "value": val,
                    "level": "Low" if val < 15 else "Normal" if val < 25 else "High" if val < 35 else "Extreme",
                    "description": "CBOE Volatility Index (Fear Gauge)"
                }
        except Exception:
            pass

        # Crude Oil (Brent) — affects Indo economy
        try:
            oil = yf.Ticker("BZ=F")
            hist = oil.history(period="5d")
            if not hist.empty:
                indicators["brent_oil"] = {
                    "value": round(hist['Close'].iloc[-1], 2),
                    "unit": "USD/barrel",
                    "description": "Brent Crude Oil Price"
                }
        except Exception:
            pass

        log.info(f"Macro indicators fetched: {len(indicators)} indicators")
        return {"source": "macro_indicators", "indicators": indicators}

    except Exception as e:
        log.error(f"Macro indicators fetch failed: {e}")
        return {"source": "macro_indicators", "error": str(e), "indicators": {}}


# ============================================================
# Bank Indonesia Rate
# ============================================================

@cached("bi_rate", ttl=3600)  # Cache 1 hour — rate doesn't change often
def fetch_bi_rate():
    """
    Fetch BI Rate (BI7DRR) info from news headlines.
    Since BI doesn't have a public API, we infer from recent news.
    """
    try:
        query = "BI Rate BI7DRR terbaru"
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=id&gl=ID&ceid=ID:id"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        headlines = []
        for item in root.findall('./channel/item')[:3]:
            title = item.find('title')
            if title is not None:
                text = title.text
                if " - " in text:
                    text = text.rsplit(" - ", 1)[0]
                headlines.append(text)

        # Try to extract rate from headlines
        rate_value = None
        for h in headlines:
            match = re.search(r'(\d+[.,]\d+)\s*%', h)
            if match:
                rate_value = float(match.group(1).replace(',', '.'))
                break

        return {
            "source": "bi_rate",
            "bi7drr": rate_value,
            "unit": "%" if rate_value else None,
            "headlines": headlines,
            "note": "Rate extracted from news; verify with official BI source"
        }
    except Exception as e:
        log.warning(f"BI Rate fetch failed: {e}")
        return {"source": "bi_rate", "error": str(e)}


# ============================================================
# Aggregator — combine all sources
# ============================================================

@cached("all_sources", ttl=TTL_MARKET_DATA)
def aggregate_all_sources(ticker=None):
    """
    Aggregate data from all available sources into one response.
    """
    log.info(f"Aggregating all data sources (ticker={ticker})")

    result = {
        "macro_indicators": fetch_indonesia_macro(),
        "bi_rate": fetch_bi_rate(),
    }

    if ticker:
        result["cnbc_news"] = fetch_cnbc_news(ticker)

    # Count successful sources
    success_count = sum(1 for v in result.values() if "error" not in v)
    result["_meta"] = {
        "sources_total": len(result) - 1,  # exclude _meta
        "sources_ok": success_count,
    }

    return result
