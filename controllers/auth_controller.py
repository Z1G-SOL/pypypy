"""
Libralex Information System
controllers/auth_controller.py

Mediates all authentication, registration, and profile operations
between the views and the UserModel.
"""

import logging
import re

from models.user_model import UserModel, VALID_ROLES

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH: int = 8


class AuthController:
    """
    Session and identity controller.

    Maintains a single ``current_user`` dict (sans ``password_hash``)
    for the duration of a login session.

    Args:
        connection: An active ``mysql.connector`` connection handle.
    """

    def __init__(self, connection) -> None:
        self.user_model: UserModel = UserModel(connection)
        self.current_user: dict | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_logged_in(self) -> bool:
        """``True`` if a user session is currently active."""
        return self.current_user is not None

    @property
    def role(self) -> str | None:
        """Role string of the active session, or ``None``."""
        return self.current_user["role"] if self.current_user else None

    @property
    def user_id(self) -> int | None:
        """Primary key of the active session's user, or ``None``."""
        return self.current_user["user_id"] if self.current_user else None

    # ------------------------------------------------------------------
    # Private guards
    # ------------------------------------------------------------------

    def _require_login(self) -> dict | None:
        """Return an error dict if no session is active, otherwise ``None``."""
        if not self.is_logged_in:
            return {"success": False, "message": "No active session. Please log in first."}
        return None

    @staticmethod
    def _validate_password_strength(password: str) -> str | None:
        """
        Check minimum password requirements.

        Args:
            password (str): Candidate plaintext password.

        Returns:
            str | None: An error message string if invalid, ``None`` if valid.
        """
        if len(password) < _MIN_PASSWORD_LENGTH:
            return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long."
        return None

    # ------------------------------------------------------------------
    # Auth operations
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> dict:
        """
        Authenticate and establish a session.

        Args:
            username (str): Login handle.
            password (str): Plaintext password.

        Returns:
            dict: ``{"success": bool, "message": str, "user": dict | None}``
        """
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
            logger.info("Session started for user '%s' (role=%s).", user["username"], user["role"])
        return result

    def logout(self) -> dict:
        """
        Terminate the active session.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        denied = self._require_login()
        if denied:
            return denied
        username = self.current_user.get("username", "User")
        self.current_user = None
        logger.info("Session ended for user '%s'.", username)
        return {"success": True, "message": f"{username} logged out successfully."}

    def register(
        self,
        username: str,
        password: str,
        confirm_password: str,
        email: str,
        full_name: str,
        role: str,
        contact_number: str | None = None,
    ) -> dict:
        """
        Register a new user account with full input validation.

        Privileged roles (``librarian``, ``admin``) require the caller to
        be an authenticated admin.

        Args:
            username (str): Desired login handle.
            password (str): Plaintext password.
            confirm_password (str): Must match *password*.
            email (str): Unique e-mail address.
            full_name (str): Display name.
            role (str): Requested role — one of ``VALID_ROLES``.
            contact_number (str | None): Optional contact string.

        Returns:
            dict: ``{"success": bool, "message": str, "user_id": int | None}``
        """
        # --- Field presence checks ---
        for field_name, value in (
            ("Username", username),
            ("Password", password),
            ("Email", email),
            ("Full name", full_name),
        ):
            if not value or not str(value).strip():
                return {"success": False, "message": f"{field_name} is required.", "user_id": None}

        if password != confirm_password:
            return {"success": False, "message": "Passwords do not match.", "user_id": None}

        pw_error = self._validate_password_strength(password)
        if pw_error:
            return {"success": False, "message": pw_error, "user_id": None}

        email_clean = email.strip()
        if not _EMAIL_RE.match(email_clean):
            return {"success": False, "message": "Invalid e-mail address format.", "user_id": None}

        role_clean = role.lower().strip()
        if role_clean not in VALID_ROLES:
            return {
                "success": False,
                "message": f"Invalid role. Must be one of: {sorted(VALID_ROLES)}",
                "user_id": None,
            }
        if role_clean in {"librarian", "admin"}:
            if not self.is_logged_in or self.role != "admin":
                return {
                    "success": False,
                    "message": "Only administrators can create librarian or admin accounts.",
                    "user_id": None,
                }

        try:
            return self.user_model.create_user(
                username=username.strip(),
                password=password,
                email=email_clean,
                role=role_clean,
                full_name=full_name.strip(),
                contact_number=contact_number,
            )
        except Exception as exc:
            logger.exception("register failed for username='%s'.", username)
            return {"success": False, "message": str(exc), "user_id": None}

    def change_password(
        self, old_password: str, new_password: str, confirm_new: str
    ) -> dict:
        """
        Change the active session user's password.

        Args:
            old_password (str): Current password for verification.
            new_password (str): Desired new password.
            confirm_new (str): Must match *new_password*.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        denied = self._require_login()
        if denied:
            return denied
        if new_password != confirm_new:
            return {"success": False, "message": "New passwords do not match."}
        pw_error = self._validate_password_strength(new_password)
        if pw_error:
            return {"success": False, "message": pw_error}
        if old_password == new_password:
            return {"success": False, "message": "New password must differ from the current password."}
        try:
            return self.user_model.change_password(self.user_id, old_password, new_password)
        except Exception as exc:
            logger.exception("change_password failed for user_id=%s.", self.user_id)
            return {"success": False, "message": str(exc)}

    def update_profile(self, **kwargs) -> dict:
        """
        Update allowed profile fields for the active session user.

        Accepted fields: ``full_name``, ``contact_number``, ``email``.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        denied = self._require_login()
        if denied:
            return denied
        safe_fields = {"full_name", "contact_number", "email"}
        updates = {k: v for k, v in kwargs.items() if k in safe_fields}
        if not updates:
            return {"success": False, "message": "No valid profile fields provided."}
        if "email" in updates and not _EMAIL_RE.match(updates["email"].strip()):
            return {"success": False, "message": "Invalid e-mail address format."}
        try:
            result = self.user_model.update_user(self.user_id, **updates)
            if result["success"]:
                refreshed = self.user_model.get_user_by_id(self.user_id)
                if refreshed:
                    refreshed.pop("password_hash", None)
                    self.current_user = refreshed
            return result
        except Exception as exc:
            logger.exception("update_profile failed for user_id=%s.", self.user_id)
            return {"success": False, "message": str(exc)}

    # ------------------------------------------------------------------
    # Admin operations
    # ------------------------------------------------------------------

    def admin_update_user(self, target_user_id: int, **kwargs) -> dict:
        """
        Admin-only: update any user account's fields.

        Args:
            target_user_id (int): The user to update.
            **kwargs: Allowed fields as per ``UserModel.update_user``.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        denied = self._require_login()
        if denied:
            return denied
        if self.role != "admin":
            return {"success": False, "message": "Only admins can update other users' accounts."}
        try:
            return self.user_model.update_user(target_user_id, **kwargs)
        except Exception as exc:
            logger.exception("admin_update_user failed for target_user_id=%s.", target_user_id)
            return {"success": False, "message": str(exc)}

    def admin_deactivate_user(self, target_user_id: int) -> dict:
        """
        Admin-only: soft-delete a user account.

        Args:
            target_user_id (int): The user to deactivate.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        denied = self._require_login()
        if denied:
            return denied
        if self.role != "admin":
            return {"success": False, "message": "Only admins can deactivate user accounts."}
        if target_user_id == self.user_id:
            return {"success": False, "message": "You cannot deactivate your own account."}
        try:
            return self.user_model.deactivate_user(target_user_id)
        except Exception as exc:
            logger.exception("admin_deactivate_user failed for target_user_id=%s.", target_user_id)
            return {"success": False, "message": str(exc)}

    def admin_get_all_users(self, role: str | None = None) -> dict:
        """
        Admin-only: retrieve all user accounts, optionally filtered by role.

        Args:
            role (str | None): Optional role filter.

        Returns:
            dict: ``{"success": bool, "message": str, "users": list[dict]}``
        """
        denied = self._require_login()
        if denied:
            return {**denied, "users": []}
        if self.role != "admin":
            return {"success": False, "message": "Only admins can view all user accounts.", "users": []}
        try:
            users = self.user_model.get_all_users(role=role)
            for u in users:
                u.pop("password_hash", None)
            return {"success": True, "message": f"{len(users)} user(s) found.", "users": users}
        except Exception as exc:
            logger.exception("admin_get_all_users failed.")
            return {"success": False, "message": str(exc), "users": []}