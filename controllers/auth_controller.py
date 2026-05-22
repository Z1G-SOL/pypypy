"""
Libralex Information System
controllers/auth_controller.py

Session management. Password strength enforced (upper+digit+symbol).
Login never reveals whether a username exists (prevents enumeration).
Privileged role creation gated to active admin session.
"""
import logging, re
from typing import Optional
from models.user_model import UserModel, VALID_ROLES

logger = logging.getLogger(__name__)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _pw_error(password: str) -> Optional[str]:
    if len(password) < 8:                    return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):    return "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):       return "Password must contain at least one digit."
    if not re.search(r"[^A-Za-z0-9]", password): return "Password must contain at least one special character."
    return None

class AuthController:
    def __init__(self, connection) -> None:
        self.user_model   = UserModel(connection)
        self.current_user: Optional[dict] = None

    @property
    def is_logged_in(self) -> bool: return self.current_user is not None
    @property
    def role(self) -> Optional[str]: return self.current_user["role"] if self.current_user else None
    @property
    def user_id(self) -> Optional[int]: return self.current_user["user_id"] if self.current_user else None

    def _require_login(self) -> Optional[dict]:
        return None if self.is_logged_in else {"success": False, "message": "No active session."}

    def login(self, username: str, password: str) -> dict:
        if not username or not username.strip(): return {"success": False, "message": "Username is required.", "user": None}
        if not password:                         return {"success": False, "message": "Password is required.", "user": None}
        result = self.user_model.authenticate(username.strip(), password)
        if result["success"]:
            user = result["user"].copy()
            user.pop("password_hash", None)
            self.current_user = user
            result["user"]    = user
            logger.info("Session started user_id=%s role=%s.", user["user_id"], user["role"])
        else:
            logger.info("Failed login for username='%s'.", username.strip())
            result["message"] = "Invalid username or password."
        return result

    def logout(self) -> dict:
        denied = self._require_login()
        if denied: return denied
        uid = self.current_user.get("user_id")
        self.current_user = None
        logger.info("Session ended user_id=%s.", uid)
        return {"success": True, "message": "Logged out successfully."}

    def register(self, username, password, confirm_password, email, full_name, role, contact_number=None) -> dict:
        for name, val in (("Username", username), ("Password", password), ("Email", email), ("Full name", full_name)):
            if not val or not str(val).strip():
                return {"success": False, "message": f"{name} is required.", "user_id": None}
        if password != confirm_password: return {"success": False, "message": "Passwords do not match.", "user_id": None}
        err = _pw_error(password)
        if err: return {"success": False, "message": err, "user_id": None}
        if not _EMAIL_RE.match(email.strip().lower()): return {"success": False, "message": "Invalid e-mail format.", "user_id": None}
        role_clean = role.lower().strip()
        if role_clean not in VALID_ROLES: return {"success": False, "message": f"Invalid role.", "user_id": None}
        if role_clean in {"librarian", "admin"} and (not self.is_logged_in or self.role != "admin"):
            return {"success": False, "message": "Only admins can create librarian/admin accounts.", "user_id": None}
        try:
            return self.user_model.create_user(username.strip(), password, email.strip().lower(),
                                               role_clean, full_name.strip(), contact_number)
        except Exception as exc:
            logger.exception("register failed.")
            return {"success": False, "message": str(exc), "user_id": None}

    def change_password(self, old_password: str, new_password: str, confirm_new: str) -> dict:
        denied = self._require_login()
        if denied: return denied
        if new_password != confirm_new:   return {"success": False, "message": "New passwords do not match."}
        err = _pw_error(new_password)
        if err: return {"success": False, "message": err}
        if old_password == new_password:  return {"success": False, "message": "New password must differ from current."}
        return self.user_model.change_password(self.user_id, old_password, new_password)

    def update_profile(self, **kwargs) -> dict:
        denied = self._require_login()
        if denied: return denied
        safe   = {"full_name", "contact_number", "email"}
        updates = {k: v for k, v in kwargs.items() if k in safe}
        if not updates: return {"success": False, "message": "No valid profile fields provided."}
        if "email" in updates:
            ec = updates["email"].strip().lower()
            if not _EMAIL_RE.match(ec): return {"success": False, "message": "Invalid e-mail format."}
            updates["email"] = ec
        result = self.user_model.update_user(self.user_id, **updates)
        if result["success"]:
            refreshed = self.user_model.get_user_by_id(self.user_id)
            if refreshed:
                refreshed.pop("password_hash", None)
                self.current_user = refreshed
        return result

    def admin_get_all_users(self, role=None) -> dict:
        denied = self._require_login()
        if denied: return {**denied, "users": []}
        if self.role != "admin": return {"success": False, "message": "Admins only.", "users": []}
        users = self.user_model.get_all_users(role=role)
        for u in users: u.pop("password_hash", None)
        return {"success": True, "message": f"{len(users)} user(s) found.", "users": users}