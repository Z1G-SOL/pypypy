"""
Libralex Information System
models/base_model.py

Shared database helper mixin used by all model classes.
Provides DRY _fetch_one / _fetch_all helpers with safe cursor lifecycle
management that survives cursor-construction failures.
"""

import logging

logger = logging.getLogger(__name__)


class BaseModel:
    """
    Abstract base for all Libralex model classes.

    Subclasses must set ``self.conn`` to an active MySQL connection before
    calling any helper method.

    Attributes:
        conn: Active ``mysql.connector`` connection handle (set by subclass).
    """

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """
        Execute *sql* and return the first matching row as a dict, or None.

        Args:
            sql (str): Parameterised SQL query string.
            params (tuple): Positional bind parameters.

        Returns:
            dict | None: First result row, or ``None`` if no rows matched.
        """
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchone()
        except Exception:
            logger.exception("_fetch_one failed. SQL: %s  Params: %s", sql, params)
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Execute *sql* and return all matching rows as a list of dicts.

        Args:
            sql (str): Parameterised SQL query string.
            params (tuple): Positional bind parameters.

        Returns:
            list[dict]: All result rows (empty list if none).
        """
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        except Exception:
            logger.exception("_fetch_all failed. SQL: %s  Params: %s", sql, params)
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def _execute(self, sql: str, params: tuple = ()) -> int:
        """
        Execute a non-SELECT statement and commit, returning ``rowcount``.
        Rolls back automatically on any exception.

        Args:
            sql (str): Parameterised DML statement.
            params (tuple): Positional bind parameters.

        Returns:
            int: Number of rows affected.

        Raises:
            Exception: Re-raises any DB error after rollback.
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            return cursor.rowcount
        except Exception:
            self.conn.rollback()
            logger.exception("_execute failed. SQL: %s  Params: %s", sql, params)
            raise
        finally:
            if cursor is not None:
                cursor.close()