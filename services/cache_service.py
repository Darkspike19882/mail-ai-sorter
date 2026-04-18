#!/usr/bin/env python3
"""
Cache-Service für Performance-Optimierung.
Cached IMAP-Verbindungen und Datenbankabfragen.
"""

import functools
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import imaplib


class CacheManager:
    """Thread-sicherer Cache mit TTL."""

    def __init__(self, default_ttl: int = 300):  # 5 Minuten Default
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._cache[key] = (value, expiry)

    def invalidate(self, pattern: Optional[str] = None) -> None:
        with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                # Remove keys matching pattern
                keys_to_remove = [
                    key for key in self._cache if pattern in key
                ]
                for key in keys_to_remove:
                    del self._cache[key]

    def cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        with self._lock:
            keys_to_remove = [
                key for key, (_, expiry) in self._cache.items()
                if expiry <= now
            ]
            for key in keys_to_remove:
                del self._cache[key]


# Globaler Cache
_cache_manager = CacheManager(default_ttl=300)  # 5 Minuten


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator für Caching von Funktionen."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            result = _cache_manager.get(cache_key)
            if result is not None:
                return result

            # Not in cache, call function
            result = func(*args, **kwargs)

            # Store in cache
            _cache_manager.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


class IMAPConnectionPool:
    """Pool für Wiederverwendung von IMAP-Verbindungen."""

    def __init__(self, max_age: int = 300):  # 5 Minuten max Alter
        self._connections: Dict[str, Tuple[imaplib.IMAP4_SSL, float]] = {}
        self._lock = threading.Lock()
        self._max_age = max_age

    def _make_key(self, account: Dict[str, Any]) -> str:
        """Erzeuge Cache-Key für Account."""
        host = account.get("imap_host", "")
        username = account.get("username", "")
        return f"{host}:{username}"

    def get(self, account: Dict[str, Any]) -> Optional[imaplib.IMAP4_SSL]:
        """Hole Verbindung aus Pool oder erstelle neue."""
        key = self._make_key(account)

        with self._lock:
            if key in self._connections:
                conn, timestamp = self._connections[key]
                # Prüfe ob Verbindung noch gültig ist
                if time.time() - timestamp < self._max_age:
                    try:
                        # Test-Verbindung
                        conn.noop()
                        return conn
                    except Exception:
                        # Verbindung ist tot, entferne
                        del self._connections[key]
                else:
                    # Zu alt, entferne
                    del self._connections[key]

        return None

    def store(self, account: Dict[str, Any], conn: imaplib.IMAP4_SSL) -> None:
        """Speichere Verbindung im Pool."""
        key = self._make_key(account)

        with self._lock:
            # Alte Verbindung entfernen falls vorhanden
            if key in self._connections:
                try:
                    old_conn, _ = self._connections[key]
                    old_conn.logout()
                except Exception:
                    pass

            self._connections[key] = (conn, time.time())

    def cleanup(self) -> None:
        """Entferne alte Verbindungen."""
        now = time.time()
        keys_to_remove = []

        with self._lock:
            for key, (_, timestamp) in self._connections.items():
                if now - timestamp > self._max_age:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                conn, _ = self._connections[key]
                try:
                    conn.logout()
                except Exception:
                    pass
                del self._connections[key]

    def clear(self) -> None:
        """Schließe alle Verbindungen."""
        with self._lock:
            for conn, _ in self._connections.values():
                try:
                    conn.logout()
                except Exception:
                    pass
            self._connections.clear()


# Globaler IMAP Pool
_imap_pool = IMAPConnectionPool()


class DatabaseCache:
    """Cache für Datenbankabfragen."""

    def __init__(self, db_path: Path, ttl: int = 300):
        self.db_path = db_path
        self.ttl = ttl

    @cached(ttl=300, key_prefix="db_stats")
    def get_stats(self) -> Dict[str, Any]:
        """Cached Statistiken."""
        return self._execute_stats_query()

    @cached(ttl=600, key_prefix="db_detailed_stats")  # 10 Minuten Cache
    def get_detailed_stats(self, days: str = "30") -> Dict[str, Any]:
        """Cached detaillierte Statistiken."""
        return self._execute_detailed_stats_query(days)

    def _execute_stats_query(self) -> Dict[str, Any]:
        """Führe Basis-Stats Query aus."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Optimierte Query mit Index-Nutzung
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

    def _execute_detailed_stats_query(self, days: str) -> Dict[str, Any]:
        """Führe detaillierte Stats Query aus (optimiert)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            where_date = ""
            if days and days != "all":
                try:
                    where_date = f" AND date_iso >= date('now', '-{int(days)} days')"
                except ValueError:
                    pass

            # Einzelne optimierte Queries statt einem großen Query
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
                # Weniger Daten für schnelleres Laden
                "category_by_account": [],
                "sender_by_category": [],
                "weekday_dist": [],
                "hour_dist": [],
                "date_range": {},
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


# Globaler DB Cache
_db_cache: Optional[DatabaseCache] = None


def get_db_cache(db_path: Optional[Path] = None) -> DatabaseCache:
    """Hole oder erstelle DB Cache."""
    global _db_cache
    if _db_cache is None:
        db_path = db_path or Path(__file__).resolve().parent.parent / "mail_index.db"
        _db_cache = DatabaseCache(db_path)
    return _db_cache


def invalidate_all_caches() -> None:
    """Invalidiere alle Caches."""
    _cache_manager.invalidate()
    _imap_pool.cleanup()


# Periodic Cleanup
def start_background_cleanup(interval: int = 300):
    """Starte periodischen Cleanup im Hintergrund."""
    import threading

    def cleanup_worker():
        while True:
            time.sleep(interval)
            _cache_manager.cleanup()
            _imap_pool.cleanup()

    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()


# Startup cleanup thread
start_background_cleanup()