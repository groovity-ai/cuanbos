import sys
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_news(ticker, limit=5):
    """
    Fetch news from Google News RSS for a given ticker.
    """
    try:
        # 1. Clean Ticker & Prepare Query
        # Remove .JK or similar suffixes for cleaner search
        clean_ticker = ticker.split('.')[0]
        
        # Query: "{TICKER} saham indonesia" or just "{TICKER} saham"
        # We want relevant financial news.
        query = f"{clean_ticker} saham"
        encoded_query = urllib.parse.quote(query)
        
        # Google News RSS URL (Indonesia edition)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=id&gl=ID&ceid=ID:id"
        
        # 2. Fetch RSS
        # Use standard urllib to avoid extra dependencies if requests is missing
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        # 3. Parse XML
        root = ET.fromstring(xml_data)
        
        news_items = []
        # XML Structure: rss -> channel -> item
        for item in root.findall('./channel/item'):
            if len(news_items) >= limit:
                break
                
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Clean Title (Google News often adds " - SourceName" at the end)
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
                
            news_items.append({
                "title": title,
                "link": link,
                "date": pub_date
            })
            
        return {
            "ticker": ticker,
            "query": query,
            "count": len(news_items),
            "news": news_items
        }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Usage: python news.py <TICKER> [LIMIT]
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python news.py <TICKER>"}))
        sys.exit(1)
        
    ticker = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    result = fetch_news(ticker, limit)
    print(json.dumps(result, indent=2))
