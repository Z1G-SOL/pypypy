"""
Libralex Information System
database/db_connection.py

Production-grade MySQL connection factory.
Credentials from environment variables — never hard-coded.

Required env vars:
    DB_HOST      (default: localhost)
    DB_PORT      (default: 3306)
    DB_USER      (default: root)
    DB_PASSWORD  (required)
    DB_NAME      (default: libralex_db)
"""
import logging, os, time
from typing import Optional
import mysql.connector
from mysql.connector import Error as MySQLError

logger = logging.getLogger(__name__)

def _build_config() -> dict:
    password = os.environ.get("DB_PASSWORD", "")
    if not password:
        logger.warning("DB_PASSWORD not set — using empty password (dev only).")
    return {
        "host":               os.environ.get("DB_HOST", "localhost"),
        "port":               int(os.environ.get("DB_PORT", "3306")),
        "user":               os.environ.get("DB_USER", "root"),
        "password":           password,
        "database":           os.environ.get("DB_NAME", "libralex_db"),
        "charset":            "utf8mb4",
        "use_pure":           True,
        "connection_timeout": 10,
        "autocommit":         False,
    }

DB_CONFIG: dict = _build_config()
_MAX_RETRIES: int   = 3
_RETRY_DELAY: float = 0.5

def get_connection(retries: int = _MAX_RETRIES) -> mysql.connector.MySQLConnection:
    """Return a healthy open MySQL connection with exponential back-off retry."""
    delay     = _RETRY_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            conn.ping(reconnect=True, attempts=1, delay=0)
            if attempt > 1:
                logger.info("DB connected on attempt %d.", attempt)
            return conn
        except MySQLError as exc:
            last_exc = exc
            logger.warning("DB attempt %d/%d failed: %s. Retry in %.1fs…", attempt, retries, exc, delay)
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise ConnectionError(
        f"Cannot connect to '{DB_CONFIG['database']}' at "
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']} after {retries} attempts.\n"
        f"Last error: {last_exc}\n"
        "Check DB_HOST / DB_USER / DB_PASSWORD / DB_NAME."
    )

def ensure_alive(conn: mysql.connector.MySQLConnection) -> mysql.connector.MySQLConnection:
    """Return conn if healthy, or a fresh connection if it has gone stale."""
    try:
        conn.ping(reconnect=False)
        return conn
    except MySQLError:
        logger.warning("Stale DB connection — reopening.")
        try:
            conn.close()
        except Exception:
            pass
        return get_connection()

def test_connection() -> dict:
    """Non-raising startup diagnostic. Returns {success, message, host, database}."""
    try:
        conn = get_connection()
        conn.close()
        return {
            "success":  True,
            "message":  f"Connected to '{DB_CONFIG['database']}' on {DB_CONFIG['host']}:{DB_CONFIG['port']}.",
            "host":     DB_CONFIG["host"],
            "database": DB_CONFIG["database"],
        }
    except Exception as exc:
        return {"success": False, "message": str(exc), "host": DB_CONFIG.get("host",""), "database": DB_CONFIG.get("database","")}