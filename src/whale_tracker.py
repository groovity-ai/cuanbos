"""
Whale Tracker 🐋
Fetches on-chain large transactions (Whale Alerts) using free APIs or heuristics.
"""

import httpx
import json
from logger import get_logger

log = get_logger("whale_tracker")

# Whale Alert free tier API or an alternative public on-chain explorer
# Since real Whale Alert requires an API key, we will use an alternative or mock
# For production, you should get a free API key from https://whale-alert.io/
# Fallback: using blockchain.info / blockchair public APIs for large txs

def get_bitcoin_whales():
    """
    Fetches recent large Bitcoin transactions (>1000 BTC).
    Using blockchain.info unconfirmed transactions as a proxy for free data.
    """
    url = "https://blockchain.info/unconfirmed-transactions?format=json"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        txs = data.get("txs", [])
        whale_txs = []
        
        for tx in txs:
            # Calculate total output value in Satoshis
            total_value_sat = sum(out.get("value", 0) for out in tx.get("out", []))
            total_btc = total_value_sat / 100_000_000
            
            # If transaction is > 500 BTC, consider it a whale
            if total_btc >= 500:
                whale_txs.append({
                    "hash": tx.get("hash"),
                    "amount_btc": round(total_btc, 2),
                    "time": tx.get("time")
                })
                
        # Sort by amount descending
        whale_txs = sorted(whale_txs, key=lambda x: x["amount_btc"], reverse=True)
        
        return {
            "status": "success",
            "count": len(whale_txs),
            "top_transactions": whale_txs[:5],
            "message": f"Found {len(whale_txs)} unconfirmed whale transactions (>500 BTC) right now."
        }
    except Exception as e:
        log.error(f"Error fetching whale data: {e}")
        return {"status": "error", "message": str(e)}

def analyze_whale_sentiment():
    """
    Combines whale data into a sentiment summary.
    """
    btc_whales = get_bitcoin_whales()
    
    if btc_whales.get("status") == "error":
        return btc_whales
        
    count = btc_whales.get("count", 0)
    if count == 0:
        sentiment = "Calm"
        explanation = "Paus lagi pada tidur. Gak ada pergerakan transaksi >500 BTC di mempool sekarang."
    elif count < 5:
        sentiment = "Moderate"
        explanation = "Ada sedikit pergerakan Paus. Market wajar, tapi tetep waspada."
    else:
        sentiment = "High Alert / Volatile"
        explanation = f"WARNING! 🐋 Ada {count} transaksi raksasa (>500 BTC) yang lagi antri di jaringan. Kemungkinan bakal ada Dump/Pump gede dalam beberapa jam ke depan!"
        
    return {
        "status": "success",
        "sentiment": sentiment,
        "explanation": explanation,
        "raw_data": btc_whales
    }

if __name__ == "__main__":
    print(json.dumps(analyze_whale_sentiment(), indent=2))
