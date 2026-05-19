"""
Libralex Information System
models/user_model.py
"""

import hashlib
import os
from datetime import datetime


def _hash_password(plain_password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest()
    return f"{salt}:{digest}"


def _verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split(":")
        check = hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest()
        return check == digest
    except ValueError:
        return False


VALID_ROLES = {"patron", "contributor", "librarian", "admin"}


class UserModel:
    def __init__(self, connection):
        self.conn = connection

    def create_user(self, username, password, email, role, full_name, contact_number=None):
        role = role.lower().strip()
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}")
        if self.get_user_by_username(username):
            return {"success": False, "message": "Username already exists.", "user_id": None}
        if self.get_user_by_email(email):
            return {"success": False, "message": "Email already registered.", "user_id": None}
        hashed = _hash_password(password)
        sql = """
            INSERT INTO users
                (username, password_hash, email, role, full_name, contact_number, date_registered, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (username.strip(), hashed, email.strip().lower(), role,
                  full_name.strip(), contact_number.strip() if contact_number else None,
                  datetime.now(), True)
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            return {"success": True, "message": "User registered successfully.", "user_id": cursor.lastrowid}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e), "user_id": None}
        finally:
            cursor.close()

    def get_user_by_id(self, user_id):
        return self._fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))

    def get_user_by_username(self, username):
        return self._fetch_one("SELECT * FROM users WHERE username = %s", (username.strip(),))

    def get_user_by_email(self, email):
        return self._fetch_one("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))

    def get_all_users(self, role=None):
        if role:
            return self._fetch_all("SELECT * FROM users WHERE role = %s ORDER BY date_registered DESC", (role.lower(),))
        return self._fetch_all("SELECT * FROM users ORDER BY date_registered DESC")

    def authenticate(self, username, password):
        user = self.get_user_by_username(username)
        if not user:
            return {"success": False, "message": "Username not found.", "user": None}
        if not user.get("is_active"):
            return {"success": False, "message": "Account is deactivated.", "user": None}
        if not _verify_password(password, user["password_hash"]):
            return {"success": False, "message": "Incorrect password.", "user": None}
        return {"success": True, "message": "Login successful.", "user": user}

    def update_user(self, user_id, **kwargs):
        allowed_fields = {"full_name", "contact_number", "email", "is_active", "role"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "role" in updates:
            updates["role"] = updates["role"].lower().strip()
            if updates["role"] not in VALID_ROLES:
                raise ValueError(f"Invalid role. Must be one of: {VALID_ROLES}")
        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE users SET {set_clause} WHERE user_id = %s"
        values = list(updates.values()) + [user_id]
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "User not found."}
            return {"success": True, "message": "User updated successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def change_password(self, user_id, old_password, new_password):
        user = self.get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "User not found."}
        if not _verify_password(old_password, user["password_hash"]):
            return {"success": False, "message": "Current password is incorrect."}
        new_hash = _hash_password(new_password)
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, user_id))
            self.conn.commit()
            return {"success": True, "message": "Password changed successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def deactivate_user(self, user_id):
        return self.update_user(user_id, is_active=False)

    def delete_user(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "User not found."}
            return {"success": True, "message": "User deleted."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def _fetch_one(self, sql, params=()):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def _fetch_all(self, sql, params=()):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
