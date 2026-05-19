"""
Libralex Information System
controllers/auth_controller.py
"""

from models.user_model import UserModel, VALID_ROLES


class AuthController:
    def __init__(self, connection):
        self.user_model   = UserModel(connection)
        self.current_user = None

    @property
    def is_logged_in(self):
        return self.current_user is not None

    @property
    def role(self):
        return self.current_user["role"] if self.current_user else None

    @property
    def user_id(self):
        return self.current_user["user_id"] if self.current_user else None

    def _require_login(self):
        if not self.is_logged_in:
            return {"success": False, "message": "No active session. Please log in first."}
        return None

    def login(self, username, password):
        if not username or not username.strip():
            return {"success": False, "message": "Username cannot be empty.", "user": None}
        if not password:
            return {"success": False, "message": "Password cannot be empty.", "user": None}
        result = self.user_model.authenticate(username.strip(), password)
        if result["success"]:
            user = result["user"].copy()
            user.pop("password_hash", None)
            self.current_user = user
            result["user"] = user
        return result

    def logout(self):
        if not self.is_logged_in:
            return {"success": False, "message": "No active session to log out from."}
        username = self.current_user.get("username", "User")
        self.current_user = None
        return {"success": True, "message": f"{username} logged out successfully."}

    def register(self, username, password, confirm_password, email, full_name, role, contact_number=None):
        if not username or not username.strip():
            return {"success": False, "message": "Username is required.", "user_id": None}
        if not password:
            return {"success": False, "message": "Password is required.", "user_id": None}
        if not email or not email.strip():
            return {"success": False, "message": "Email is required.", "user_id": None}
        if not full_name or not full_name.strip():
            return {"success": False, "message": "Full name is required.", "user_id": None}
        if password != confirm_password:
            return {"success": False, "message": "Passwords do not match.", "user_id": None}
        if len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters long.", "user_id": None}
        role = role.lower().strip()
        if role not in VALID_ROLES:
            return {"success": False, "message": f"Invalid role. Must be one of: {sorted(VALID_ROLES)}", "user_id": None}
        if role in {"librarian", "admin"}:
            if not self.is_logged_in or self.role != "admin":
                return {"success": False, "message": "Only administrators can create librarian or admin accounts.", "user_id": None}
        try:
            return self.user_model.create_user(
                username=username.strip(), password=password,
                email=email.strip(), role=role,
                full_name=full_name.strip(), contact_number=contact_number)
        except Exception as e:
            return {"success": False, "message": str(e), "user_id": None}

    def change_password(self, old_password, new_password, confirm_new):
        denied = self._require_login()
        if denied:
            return denied
        if new_password != confirm_new:
            return {"success": False, "message": "New passwords do not match."}
        if len(new_password) < 8:
            return {"success": False, "message": "New password must be at least 8 characters long."}
        if old_password == new_password:
            return {"success": False, "message": "New password must differ from the current password."}
        try:
            return self.user_model.change_password(self.user_id, old_password, new_password)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_profile(self, **kwargs):
        denied = self._require_login()
        if denied:
            return denied
        safe_fields = {"full_name", "contact_number", "email"}
        updates = {k: v for k, v in kwargs.items() if k in safe_fields}
        if not updates:
            return {"success": False, "message": "No valid profile fields provided."}
        try:
            result = self.user_model.update_user(self.user_id, **updates)
            if result["success"]:
                refreshed = self.user_model.get_user_by_id(self.user_id)
                if refreshed:
                    refreshed.pop("password_hash", None)
                    self.current_user = refreshed
            return result
        except Exception as e:
            return {"success": False, "message": str(e)}

    def admin_update_user(self, target_user_id, **kwargs):
        denied = self._require_login()
        if denied:
            return denied
        if self.role != "admin":
            return {"success": False, "message": "Only admins can update other users' accounts."}
        try:
            return self.user_model.update_user(target_user_id, **kwargs)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def admin_deactivate_user(self, target_user_id):
        denied = self._require_login()
        if denied:
            return denied
        if self.role != "admin":
            return {"success": False, "message": "Only admins can deactivate user accounts."}
        if target_user_id == self.user_id:
            return {"success": False, "message": "You cannot deactivate your own account."}
        try:
            return self.user_model.deactivate_user(target_user_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def admin_get_all_users(self, role=None):
        denied = self._require_login()
        if denied:
            return {**denied, "users": []}
        if self.role != "admin":
            return {"success": False, "message": "Only admins can "
                                                 "view all user accounts.", "users": []}
        try:
            users = self.user_model.get_all_users(role=role)
            for u in users:
                u.pop("password_hash", None)
            return {"success": True, "message": f"{len(users)} user(s) found.", "users": users}
        except Exception as e:
            return {"success": False, "message": str(e), "users": []}
