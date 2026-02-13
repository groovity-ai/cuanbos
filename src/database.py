import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# DB Config (from docker-compose env)
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "cuanbot")
DB_PASS = os.getenv("DB_PASSWORD", "cuanbot_secret")
DB_NAME = os.getenv("DB_NAME", "cuanbot")

def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def save_analysis(symbol, price, analysis):
    """
    Save technical analysis result to daily_analysis table.
    """
    conn = get_connection()
    if not conn:
        return False
        
    try:
        cur = conn.cursor()
        
        # Ensure symbol exists in watchlist (auto-add if not)
        cur.execute(
            "INSERT INTO watchlist (symbol, asset_type) VALUES (%s, %s) ON CONFLICT (symbol) DO NOTHING",
            (symbol, 'stock' if '.JK' in symbol else 'crypto')
        )
        
        # Insert Analysis
        trend = analysis.get("trend", {}).get("status", "Unknown")
        rsi = analysis.get("momentum", {}).get("rsi", 0)
        verdict = analysis.get("verdict", "Neutral")
        
        # Format anomalies as string
        anomalies_data = analysis.get("anomalies", {})
        anomalies_str = ", ".join(anomalies_data.get("flags", []))
        if not anomalies_str and anomalies_data.get("is_gorengan"):
            anomalies_str = "Gorengan Detected"
            
        today = datetime.now().date()
        
        query = """
            INSERT INTO daily_analysis 
            (symbol, analysis_date, price, trend_status, rsi, verdict, anomalies)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, analysis_date) 
            DO UPDATE SET 
                price = EXCLUDED.price,
                trend_status = EXCLUDED.trend_status,
                rsi = EXCLUDED.rsi,
                verdict = EXCLUDED.verdict,
                anomalies = EXCLUDED.anomalies,
                created_at = CURRENT_TIMESTAMP
        """
        
        cur.execute(query, (symbol, today, price, trend, rsi, verdict, anomalies_str))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return False

def get_latest_analysis(symbol):
    conn = get_connection()
    if not conn:
        return None
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM daily_analysis WHERE symbol = %s ORDER BY analysis_date DESC LIMIT 1",
            (symbol,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Error fetching analysis: {e}")
        return None

def add_portfolio_position(symbol, asset_type, entry_price, qty, sl_pct=-5, tp_pct=10):
    """Add a new position to the portfolio table."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO portfolio (symbol, asset_type, entry_price, qty, sl_pct, tp_pct)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (symbol, asset_type, entry_price, qty, sl_pct, tp_pct)
        )
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return dict(result)
    except Exception as e:
        print(f"Error adding position: {e}")
        conn.rollback()
        return None

def get_portfolio():
    """Fetch all positions from the portfolio table."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM portfolio ORDER BY created_at DESC")
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return []

def delete_portfolio_position(position_id):
    """Delete a position by ID."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM portfolio WHERE id = %s", (position_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        return deleted
    except Exception as e:
        print(f"Error deleting position: {e}")
        return False
