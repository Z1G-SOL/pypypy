"""
Libralex Information System
models/base_model.py

Shared DB helper mixin. All DML auto-commits and auto-rolls-back.
Connection health is checked before every query.
"""
import logging
from typing import Optional
from database.db_connection import ensure_alive

logger = logging.getLogger(__name__)

class BaseModel:
    """Abstract base — subclass must set self.conn before calling any helper."""

    def _check_conn(self) -> None:
        self.conn = ensure_alive(self.conn)

    def _fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        self._check_conn()
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchone()
        except Exception:
            logger.exception("_fetch_one failed. SQL: %s", sql[:120])
            raise
        finally:
            if cursor: cursor.close()

    def _fetch_all(self, sql: str, params: tuple = ()) -> list:
        self._check_conn()
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        except Exception:
            logger.exception("_fetch_all failed. SQL: %s", sql[:120])
            raise
        finally:
            if cursor: cursor.close()

    def _execute(self, sql: str, params: tuple = ()) -> int:
        self._check_conn()
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            return cursor.rowcount
        except Exception:
            try: self.conn.rollback()
            except Exception: logger.warning("Rollback failed.")
            logger.exception("_execute failed. SQL: %s", sql[:120])
            raise
        finally:
            if cursor: cursor.close()

    def _execute_returning_id(self, sql: str, params: tuple = ()) -> int:
        self._check_conn()
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            return cursor.lastrowid
        except Exception:
            try: self.conn.rollback()
            except Exception: logger.warning("Rollback failed.")
            logger.exception("_execute_returning_id failed. SQL: %s", sql[:120])
            raise
        finally:
            if cursor: cursor.close()