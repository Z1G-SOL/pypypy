"""
Libralex Information System
models/user_model.py

Handles all persistence operations for the ``users`` table.

Password Security
-----------------
Passwords are hashed with **bcrypt** (work factor 12) — a purpose-built,
adaptive, slow hashing algorithm.  The previous SHA-256 scheme was
cryptographically insecure for password storage and has been replaced.
"""

import logging
import re
from datetime import datetime

import bcrypt

from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_ROLES: frozenset[str] = frozenset({"patron", "contributor", "librarian", "admin"})

# Simple RFC-5322-inspired email pattern — not exhaustive, but rejects obvious junk.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# bcrypt work factor — increase over time as hardware gets faster.
_BCRYPT_ROUNDS: int = 12


def _hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Args:
        plain_password (str): The user-supplied plaintext password.

    Returns:
        str: The bcrypt hash string (includes salt and work factor).
    """
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def _verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of a plaintext password against a bcrypt hash.

    Args:
        plain_password (str): The user-supplied plaintext candidate.
        stored_hash (str): The bcrypt hash retrieved from the database.

    Returns:
        bool: ``True`` if the password matches, ``False`` otherwise.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        logger.warning("Password verification encountered a malformed hash.", exc_info=True)
        return False


class UserModel(BaseModel):
    """
    Data-access object for the ``users`` table.

    Args:
        connection: An active ``mysql.connector`` connection handle.
    """

    def __init__(self, connection) -> None:
        self.conn = connection

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        role: str,
        full_name: str,
        contact_number: str | None = None,
    ) -> dict:
        """
        Register a new user account.

        Args:
            username (str): Unique login handle.
            password (str): Plaintext password (will be hashed).
            email (str): Unique e-mail address.
            role (str): One of ``VALID_ROLES``.
            full_name (str): Display name.
            contact_number (str | None): Optional phone/contact string.

        Returns:
            dict: ``{"success": bool, "message": str, "user_id": int | None}``
        """
        role = role.lower().strip()
        if role not in VALID_ROLES:
            return {
                "success": False,
                "message": f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}",
                "user_id": None,
            }
        email_clean = email.strip().lower()
        if not _EMAIL_RE.match(email_clean):
            return {"success": False, "message": "Invalid e-mail address format.", "user_id": None}
        if self.get_user_by_username(username):
            return {"success": False, "message": "Username already exists.", "user_id": None}
        if self.get_user_by_email(email_clean):
            return {"success": False, "message": "Email already registered.", "user_id": None}

        hashed = _hash_password(password)
        sql = """
            INSERT INTO users
                (username, password_hash, email, role, full_name, contact_number,
                 date_registered, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            username.strip(), hashed, email_clean, role, full_name.strip(),
            contact_number.strip() if contact_number else None,
            datetime.now(), True,
        )
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("User '%s' created with role '%s' (id=%s).", username, role, new_id)
            return {"success": True, "message": "User registered successfully.", "user_id": new_id}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("create_user failed for username='%s'.", username)
            return {"success": False, "message": str(exc), "user_id": None}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Return the user row for *user_id*, or ``None``."""
        return self._fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))

    def get_user_by_username(self, username: str) -> dict | None:
        """Return the user row matching *username* (case-insensitive), or ``None``."""
        return self._fetch_one(
            "SELECT * FROM users WHERE username = %s", (username.strip(),)
        )

    def get_user_by_email(self, email: str) -> dict | None:
        """Return the user row matching *email*, or ``None``."""
        return self._fetch_one(
            "SELECT * FROM users WHERE email = %s", (email.strip().lower(),)
        )

    def get_all_users(self, role: str | None = None) -> list[dict]:
        """
        Return all users, optionally filtered by *role*.

        Args:
            role (str | None): Optional role filter.

        Returns:
            list[dict]: User rows (password_hash included — strip at controller layer).
        """
        if role:
            return self._fetch_all(
                "SELECT * FROM users WHERE role = %s ORDER BY date_registered DESC",
                (role.lower().strip(),),
            )
        return self._fetch_all("SELECT * FROM users ORDER BY date_registered DESC")

    def get_user_counts_by_role(self) -> dict[str, int]:
        """
        Return a mapping of role → count via a single aggregation query.

        Returns:
            dict[str, int]: e.g. ``{"patron": 42, "contributor": 5, ...}``
        """
        rows = self._fetch_all("SELECT role, COUNT(*) AS cnt FROM users GROUP BY role")
        counts: dict[str, int] = {r: 0 for r in VALID_ROLES}
        for row in rows:
            counts[row["role"]] = row["cnt"]
        return counts

    # ------------------------------------------------------------------
    # Authenticate
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> dict:
        """
        Validate credentials and return the user record on success.

        Args:
            username (str): Login handle.
            password (str): Plaintext candidate password.

        Returns:
            dict: ``{"success": bool, "message": str, "user": dict | None}``
        """
        user = self.get_user_by_username(username)
        if not user:
            return {"success": False, "message": "Username not found.", "user": None}
        if not user.get("is_active"):
            return {"success": False, "message": "Account is deactivated.", "user": None}
        if not _verify_password(password, user["password_hash"]):
            return {"success": False, "message": "Incorrect password.", "user": None}
        logger.info("User '%s' authenticated successfully.", username)
        return {"success": True, "message": "Login successful.", "user": user}

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_user(self, user_id: int, **kwargs) -> dict:
        """
        Update one or more allowed fields on a user record.

        Args:
            user_id (int): Target user's primary key.
            **kwargs: Field-value pairs. Allowed: ``full_name``, ``contact_number``,
                      ``email``, ``is_active``, ``role``.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        allowed_fields = {"full_name", "contact_number", "email", "is_active", "role"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "role" in updates:
            updates["role"] = updates["role"].lower().strip()
            if updates["role"] not in VALID_ROLES:
                return {
                    "success": False,
                    "message": f"Invalid role. Must be one of: {sorted(VALID_ROLES)}",
                }
        if "email" in updates:
            email_clean = updates["email"].strip().lower()
            if not _EMAIL_RE.match(email_clean):
                return {"success": False, "message": "Invalid e-mail address format."}
            updates["email"] = email_clean

        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE users SET {set_clause} WHERE user_id = %s"
        values = list(updates.values()) + [user_id]
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "User not found."}
            return {"success": True, "message": "User updated successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("update_user failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        """
        Change a user's password after verifying the current one.

        Args:
            user_id (int): The user's primary key.
            old_password (str): Current plaintext password for verification.
            new_password (str): New plaintext password to set.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "User not found."}
        if not _verify_password(old_password, user["password_hash"]):
            return {"success": False, "message": "Current password is incorrect."}
        new_hash = _hash_password(new_password)
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (new_hash, user_id),
            )
            self.conn.commit()
            logger.info("Password changed for user_id=%s.", user_id)
            return {"success": True, "message": "Password changed successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("change_password failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    def deactivate_user(self, user_id: int) -> dict:
        """Soft-delete a user by setting ``is_active = False``."""
        return self.update_user(user_id, is_active=False)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_user(self, user_id: int) -> dict:
        """
        Hard-delete a user record. Prefer ``deactivate_user`` in production.

        Args:
            user_id (int): Target user's primary key.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "User not found."}
            logger.warning("User id=%s permanently deleted.", user_id)
            return {"success": True, "message": "User deleted."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("delete_user failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()