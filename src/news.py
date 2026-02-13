"""
News fetcher for CuanBot.
Fetches financial news from Google News RSS with caching.
"""

import sys
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from cache import cached, TTL_NEWS
from logger import get_logger

log = get_logger("news")


@cached("news", ttl=TTL_NEWS)
def fetch_news(ticker, limit=5):
    """
    Fetch news from Google News RSS + CNBC Indonesia.
    Results are cached for 30 minutes.
    """
    try:
        clean_ticker = ticker.split('.')[0]
        query = f"{clean_ticker} saham"
        encoded_query = urllib.parse.quote(query)

        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
        log.info(f"Fetching news: {ticker} (query={query})")

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        news_items = []
        for item in root.findall('./channel/item'):
            if len(news_items) >= limit:
                break

            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

            if " - " in title:
                title = title.rsplit(" - ", 1)[0]

            news_items.append({
                "title": title,
                "link": link,
                "date": pub_date,
                "source": "Google News"
            })

        # Enrich with CNBC Indonesia
        try:
            from data_sources import fetch_cnbc_news
            cnbc = fetch_cnbc_news(ticker, limit=3)
            for item in cnbc.get("news", []):
                news_items.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", ""),
                    "source": item.get("source", "CNBC Indonesia"),
                })
        except Exception as e:
            log.warning(f"CNBC news fetch failed, continuing with Google only: {e}")

        return {
            "ticker": ticker,
            "query": query,
            "count": len(news_items),
            "sources": ["Google News", "CNBC Indonesia"],
            "news": news_items
        }

    except Exception as e:
        log.error(f"Error fetching news for {ticker}: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python news.py <TICKER>"}))
        sys.exit(1)

    ticker = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    result = fetch_news(ticker, limit)
    print(json.dumps(result, indent=2))
