#!/usr/bin/env python3

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DB = BASE_DIR / "mail_index.db"


def get_stats():
    """Get stats mit Caching für bessere Performance."""
    try:
        from services.cache_service import get_db_cache

        cache = get_db_cache(INDEX_DB)
        return cache.get_stats()
    except Exception:
        # Fallback auf direkte DB-Abfrage wenn Cache nicht verfügbar
        return _get_stats_uncached()


def _get_stats_uncached():
    """Fallback ohne Cache."""
    try:
        conn = sqlite3.connect(INDEX_DB)
        cursor = conn.cursor()
        total = cursor.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        categories = cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM emails
            GROUP BY category
            ORDER BY count DESC
            """
        ).fetchall()
        accounts = cursor.execute(
            """
            SELECT account, COUNT(*) as count
            FROM emails
            GROUP BY account
            ORDER BY count DESC
            """
        ).fetchall()
        conn.close()
        return {
            "total": total,
            "categories": dict(categories),
            "accounts": dict(accounts),
        }
    except Exception as e:
        return {"error": str(e)}


def get_detailed_stats(days="30"):
    """Get detaillierte Stats mit Caching für bessere Dashboard-Performance."""
    try:
        from services.cache_service import get_db_cache

        cache = get_db_cache(INDEX_DB)
        return cache.get_detailed_stats(days)
    except Exception:
        # Fallback auf direkte DB-Abfrage wenn Cache nicht verfügbar
        return _get_detailed_stats_uncached(days)


def _get_detailed_stats_uncached(days="30"):
    """Fallback ohne Cache."""
    try:
        conn = sqlite3.connect(INDEX_DB)
        cursor = conn.cursor()
        where_date = ""
        if days and days != "all":
            try:
                where_date = f" AND date_iso >= date('now', '-{int(days)} days')"
            except ValueError:
                pass
        total = cursor.execute(
            f"SELECT COUNT(*) FROM emails WHERE 1=1{where_date}"
        ).fetchone()[0]
        categories = cursor.execute(
            f"SELECT category, COUNT(*) as count FROM emails WHERE 1=1{where_date} GROUP BY category ORDER BY count DESC"
        ).fetchall()
        accounts = cursor.execute(
            f"SELECT account, COUNT(*) as count FROM emails WHERE 1=1{where_date} GROUP BY account ORDER BY count DESC"
        ).fetchall()
        top_senders = cursor.execute(
            f"SELECT from_addr, COUNT(*) as count FROM emails WHERE 1=1{where_date} GROUP BY from_addr ORDER BY count DESC LIMIT 20"
        ).fetchall()
        daily_volume = cursor.execute(
            f"SELECT SUBSTR(date_iso, 1, 10) as day, COUNT(*) as count FROM emails WHERE date_iso IS NOT NULL{where_date} GROUP BY day ORDER BY day DESC LIMIT 30"
        ).fetchall()
        monthly_volume = cursor.execute(
            "SELECT SUBSTR(date_iso, 1, 7) as month, COUNT(*) as count FROM emails WHERE date_iso IS NOT NULL GROUP BY month ORDER BY month DESC LIMIT 12"
        ).fetchall()
        category_by_account = cursor.execute(
            f"SELECT account, category, COUNT(*) as count FROM emails WHERE 1=1{where_date} GROUP BY account, category ORDER BY account, count DESC"
        ).fetchall()
        sender_by_category = cursor.execute(
            f"SELECT category, from_addr, COUNT(*) as count FROM emails WHERE 1=1{where_date} GROUP BY category, from_addr ORDER BY category, count DESC"
        ).fetchall()
        weekday_dist = cursor.execute(
            f"SELECT CAST(STRFTIME('%w', date_iso) AS INTEGER) as dow, COUNT(*) as count FROM emails WHERE date_iso IS NOT NULL{where_date} GROUP BY dow ORDER BY dow"
        ).fetchall()
        hour_dist = cursor.execute(
            f"SELECT CAST(STRFTIME('%H', date_iso) AS INTEGER) as hour, COUNT(*) as count FROM emails WHERE date_iso IS NOT NULL{where_date} GROUP BY hour ORDER BY hour"
        ).fetchall()
        date_range = cursor.execute(
            "SELECT MIN(date_iso), MAX(date_iso) FROM emails"
        ).fetchone()
        conn.close()
        return {
            "total": total,
            "categories": dict(categories),
            "accounts": dict(accounts),
            "top_senders": [{"sender": r[0], "count": r[1]} for r in top_senders],
            "daily_volume": [
                {"date": r[0], "count": r[1]} for r in reversed(daily_volume)
            ],
            "monthly_volume": [
                {"month": r[0], "count": r[1]} for r in reversed(monthly_volume)
            ],
            "category_by_account": [
                {"account": r[0], "category": r[1], "count": r[2]}
                for r in category_by_account
            ],
            "sender_by_category": [
                {"category": r[0], "sender": r[1], "count": r[2]}
                for r in sender_by_category
            ],
            "weekday_dist": [{"day": r[0], "count": r[1]} for r in weekday_dist],
            "hour_dist": [{"hour": r[0], "count": r[1]} for r in hour_dist],
            "date_range": {"oldest": date_range[0], "newest": date_range[1]},
        }
    except Exception as e:
        return {
            "error": str(e),
            "total": 0,
            "categories": {},
            "accounts": {},
            "top_senders": [],
            "daily_volume": [],
            "monthly_volume": [],
            "category_by_account": [],
            "sender_by_category": [],
            "weekday_dist": [],
            "hour_dist": [],
            "date_range": {},
        }
