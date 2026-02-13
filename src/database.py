"""
Database layer with connection pooling for CuanBot.
Uses psycopg2 SimpleConnectionPool for efficient connection reuse.
"""

import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from logger import get_logger

log = get_logger("database")

# DB Config (from docker-compose env)
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "cuanbot")
DB_PASS = os.getenv("DB_PASSWORD", "cuanbot_secret")
DB_NAME = os.getenv("DB_NAME", "cuanbot")

# Connection Pool (lazy-init)
_pool = None


def _get_pool():
    """Lazy-init the connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        try:
            _pool = SimpleConnectionPool(
                minconn=2,
                maxconn=10,
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
            )
            log.info("Database connection pool created (2-10 connections)")
        except Exception as e:
            log.error(f"Failed to create connection pool: {e}")
            _pool = None
    return _pool


@contextmanager
def get_connection():
    """
    Context manager that gets a connection from the pool
    and returns it automatically when done.

    Usage:
        with get_connection() as conn:
            cur = conn.cursor()
            ...
    """
    pool = _get_pool()
    if pool is None:
        log.error("No database pool available")
        yield None
        return

    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        log.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        yield None
    finally:
        if conn:
            pool.putconn(conn)


def close_pool():
    """Close the connection pool gracefully."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        log.info("Database connection pool closed")
        _pool = None


def save_analysis(symbol, price, analysis):
    """Save technical analysis result to daily_analysis table."""
    with get_connection() as conn:
        if not conn:
            return False
        try:
            cur = conn.cursor()

            # Ensure symbol exists in watchlist (auto-add if not)
            cur.execute(
                "INSERT INTO watchlist (symbol, asset_type) VALUES (%s, %s) ON CONFLICT (symbol) DO NOTHING",
                (symbol, 'stock' if '.JK' in symbol else 'crypto')
            )

            # Extract analysis fields
            trend = analysis.get("trend", {}).get("status", "Unknown")
            rsi = analysis.get("momentum", {}).get("rsi", 0)
            verdict = analysis.get("verdict", "Neutral")

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
            log.info(f"Analysis saved: {symbol} @ {price}")
            return True
        except Exception as e:
            log.error(f"Error saving analysis for {symbol}: {e}")
            conn.rollback()
            return False


def get_latest_analysis(symbol):
    """Get latest analysis for a symbol."""
    with get_connection() as conn:
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
            return dict(result) if result else None
        except Exception as e:
            log.error(f"Error fetching analysis for {symbol}: {e}")
            return None


def add_portfolio_position(symbol, asset_type, entry_price, qty, sl_pct=-5, tp_pct=10):
    """Add a new position to the portfolio table."""
    with get_connection() as conn:
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
            log.info(f"Portfolio position added: {symbol} x{qty} @ {entry_price}")
            return dict(result)
        except Exception as e:
            log.error(f"Error adding position {symbol}: {e}")
            conn.rollback()
            return None


def get_portfolio():
    """Fetch all positions from the portfolio table."""
    with get_connection() as conn:
        if not conn:
            return []
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM portfolio ORDER BY created_at DESC")
            results = cur.fetchall()
            cur.close()
            return [dict(r) for r in results]
        except Exception as e:
            log.error(f"Error fetching portfolio: {e}")
            return []


def delete_portfolio_position(position_id):
    """Delete a position by ID."""
    with get_connection() as conn:
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM portfolio WHERE id = %s", (position_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            cur.close()
            if deleted:
                log.info(f"Portfolio position deleted: ID {position_id}")
            return deleted
        except Exception as e:
            log.error(f"Error deleting position {position_id}: {e}")
            conn.rollback()
            return False


# ============================================================
# Analysis History (JSONB snapshots for time-series tracking)
# ============================================================

def save_analysis_history(symbol, analysis_type, data):
    """
    Save a full analysis snapshot to the history table (JSONB).
    Returns the inserted row id, or None on failure.
    """
    with get_connection() as conn:
        if not conn:
            return None
        try:
            import json
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO analysis_history (symbol, analysis_type, analysis_data)
                   VALUES (%s, %s, %s::jsonb) RETURNING id""",
                (symbol, analysis_type, json.dumps(data, default=str))
            )
            row_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            log.info(f"History saved: {symbol}/{analysis_type} → id={row_id}")
            return row_id
        except Exception as e:
            log.error(f"Error saving history for {symbol}/{analysis_type}: {e}")
            conn.rollback()
            return None


def get_analysis_history(symbol, analysis_type=None, limit=10, offset=0):
    """
    Fetch recent analysis history for a symbol.
    Optionally filter by analysis_type.
    """
    with get_connection() as conn:
        if not conn:
            return []
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if analysis_type:
                cur.execute(
                    """SELECT id, symbol, analysis_type, analysis_data, created_at
                       FROM analysis_history
                       WHERE symbol = %s AND analysis_type = %s
                       ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (symbol, analysis_type, limit, offset)
                )
            else:
                cur.execute(
                    """SELECT id, symbol, analysis_type, analysis_data, created_at
                       FROM analysis_history
                       WHERE symbol = %s
                       ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (symbol, limit, offset)
                )
            results = cur.fetchall()
            cur.close()
            return [dict(r) for r in results]
        except Exception as e:
            log.error(f"Error fetching history for {symbol}: {e}")
            return []


def get_analysis_trend(symbol, days=30):
    """
    Get time-series data for a symbol over N days.
    Returns list of {date, price, rsi, verdict} from daily_analysis.
    """
    with get_connection() as conn:
        if not conn:
            return []
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """SELECT analysis_date, price, rsi, trend_status, verdict
                   FROM daily_analysis
                   WHERE symbol = %s
                     AND analysis_date >= CURRENT_DATE - INTERVAL '%s days'
                   ORDER BY analysis_date ASC""",
                (symbol, days)
            )
            results = cur.fetchall()
            cur.close()
            return [dict(r) for r in results]
        except Exception as e:
            log.error(f"Error fetching trend for {symbol}: {e}")
            return []


def save_feedback(analysis_id, symbol, rating, comment=None):
    """
    Save user feedback (👍 = 1, 👎 = -1) on an analysis.
    """
    with get_connection() as conn:
        if not conn:
            return None
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """INSERT INTO ai_feedback (analysis_id, symbol, rating, comment)
                   VALUES (%s, %s, %s, %s) RETURNING *""",
                (analysis_id, symbol, rating, comment)
            )
            result = cur.fetchone()
            conn.commit()
            cur.close()
            log.info(f"Feedback saved: {symbol} analysis #{analysis_id} → {'👍' if rating == 1 else '👎'}")
            return dict(result)
        except Exception as e:
            log.error(f"Error saving feedback: {e}")
            conn.rollback()
            return None


def get_feedback_stats(symbol=None):
    """
    Get accuracy stats from user feedback.
    If symbol given, return stats per symbol. Otherwise, global stats.
    """
    with get_connection() as conn:
        if not conn:
            return {}
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if symbol:
                cur.execute(
                    """SELECT
                         COUNT(*) as total,
                         SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as positive,
                         SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as negative,
                         ROUND(AVG(rating)::numeric, 2) as avg_rating
                       FROM ai_feedback WHERE symbol = %s""",
                    (symbol,)
                )
            else:
                cur.execute(
                    """SELECT
                         COUNT(*) as total,
                         SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as positive,
                         SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) as negative,
                         ROUND(AVG(rating)::numeric, 2) as avg_rating
                       FROM ai_feedback"""
                )
            result = cur.fetchone()
            cur.close()
            if result:
                stats = dict(result)
                total = stats.get("total", 0)
                positive = stats.get("positive", 0)
                stats["accuracy_pct"] = round(positive / total * 100, 1) if total > 0 else None
                return stats
            return {"total": 0, "positive": 0, "negative": 0, "accuracy_pct": None}
        except Exception as e:
            log.error(f"Error fetching feedback stats: {e}")
            return {}

