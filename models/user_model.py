"""
Libralex Information System
models/user_model.py

DAL for the users table. bcrypt password hashing, full input validation,
optimistic existence guard on updates, password_hash never logged.
"""
import logging, re
from datetime import datetime
from typing import Optional
import bcrypt
from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_ROLES: frozenset = frozenset({"patron", "contributor", "librarian", "admin"})
_EMAIL_RE        = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_USERNAME_LEN = 3
_BCRYPT_ROUNDS    = 12

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")

def _verify_password(plain: str, stored: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        logger.warning("Malformed stored hash during verification.")
        return False

class UserModel(BaseModel):
    def __init__(self, connection) -> None:
        self.conn = connection

    @staticmethod
    def _validate_email(email: str) -> Optional[str]:
        return None if _EMAIL_RE.match(email) else "Invalid e-mail address format."

    @staticmethod
    def _validate_role(role: str) -> Optional[str]:
        return None if role in VALID_ROLES else f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}."

    @staticmethod
    def _validate_username(username: str) -> Optional[str]:
        if len(username) < _MIN_USERNAME_LEN:
            return f"Username must be at least {_MIN_USERNAME_LEN} characters."
        if not re.match(r"^[\w.\-]+$", username):
            return "Username may only contain letters, digits, '.', '_', '-'."
        return None

    def create_user(self, username, password, email, role, full_name, contact_number=None) -> dict:
        u = username.strip(); e = email.strip().lower(); r = role.lower().strip(); fn = full_name.strip()
        for err in (self._validate_username(u), self._validate_email(e), self._validate_role(r)):
            if err: return {"success": False, "message": err, "user_id": None}
        if self.get_user_by_username(u): return {"success": False, "message": "Username already exists.", "user_id": None}
        if self.get_user_by_email(e):    return {"success": False, "message": "Email already registered.", "user_id": None}
        sql = """INSERT INTO users (username,password_hash,email,role,full_name,contact_number,date_registered,is_active)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(sql, (u, _hash_password(password), e, r, fn,
                                 contact_number.strip() if contact_number else None,
                                 datetime.now(), True))
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("User registered id=%s role=%s.", new_id, r)
            return {"success": True, "message": "User registered successfully.", "user_id": new_id}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            logger.exception("create_user failed.")
            return {"success": False, "message": str(exc), "user_id": None}
        finally:
            if cursor: cursor.close()

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))

    def get_user_by_username(self, username: str) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM users WHERE username = %s", (username.strip(),))

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))

    def get_all_users(self, role: Optional[str] = None) -> list:
        if role:
            return self._fetch_all("SELECT * FROM users WHERE role = %s ORDER BY date_registered DESC", (role.lower().strip(),))
        return self._fetch_all("SELECT * FROM users ORDER BY date_registered DESC")

    def get_user_counts_by_role(self) -> dict:
        rows   = self._fetch_all("SELECT role, COUNT(*) AS cnt FROM users GROUP BY role")
        counts = {r: 0 for r in VALID_ROLES}
        for row in rows: counts[row["role"]] = row["cnt"]
        return counts

    def authenticate(self, username: str, password: str) -> dict:
        user = self.get_user_by_username(username)
        if not user:                               return {"success": False, "message": "Invalid username or password.", "user": None}
        if not user.get("is_active"):              return {"success": False, "message": "Account is deactivated. Contact support.", "user": None}
        if not _verify_password(password, user["password_hash"]): return {"success": False, "message": "Invalid username or password.", "user": None}
        logger.info("User id=%s authenticated.", user["user_id"])
        return {"success": True, "message": "Login successful.", "user": user}

    def update_user(self, user_id: int, **kwargs) -> dict:
        allowed = {"full_name", "contact_number", "email", "is_active", "role"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates: return {"success": False, "message": "No valid fields provided."}
        if "role" in updates:
            updates["role"] = updates["role"].lower().strip()
            err = self._validate_role(updates["role"])
            if err: return {"success": False, "message": err}
        if "email" in updates:
            updates["email"] = updates["email"].strip().lower()
            err = self._validate_email(updates["email"])
            if err: return {"success": False, "message": err}
        if not self.get_user_by_id(user_id): return {"success": False, "message": "User not found."}
        set_clause = ", ".join(f"{f} = %s" for f in updates)
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s", list(updates.values()) + [user_id])
            self.conn.commit()
            if cursor.rowcount == 0: return {"success": False, "message": "No changes made."}
            return {"success": True, "message": "User updated successfully."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        user = self.get_user_by_id(user_id)
        if not user: return {"success": False, "message": "User not found."}
        if not _verify_password(old_password, user["password_hash"]): return {"success": False, "message": "Current password is incorrect."}
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (_hash_password(new_password), user_id))
            self.conn.commit()
            logger.info("Password changed for user_id=%s.", user_id)
            return {"success": True, "message": "Password changed successfully."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def deactivate_user(self, user_id: int) -> dict:
        return self.update_user(user_id, is_active=False)

    def delete_user(self, user_id: int) -> dict:
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            self.conn.commit()
            if cursor.rowcount == 0: return {"success": False, "message": "User not found."}
            logger.warning("User id=%s permanently deleted.", user_id)
            return {"success": True, "message": "User deleted."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()