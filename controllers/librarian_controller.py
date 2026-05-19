"""
Libralex Information System
controllers/librarian_controller.py

Aggregate controller for librarian and admin dashboard operations.
Delegates to CatalogController, SubmissionController, and direct model
access where a single privileged action spans multiple models.
"""

import logging

from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from models.user_model import UserModel
from models.review_model import ReviewModel

logger = logging.getLogger(__name__)


class LibrarianController:
    """
    High-level controller scoped to librarian/admin users.

    Instantiation raises ``PermissionError`` if the supplied *current_user*
    does not hold the ``librarian`` or ``admin`` role.

    Args:
        connection: An active ``mysql.connector`` connection handle.
        current_user (dict): Authenticated user dict (must be librarian/admin).
    """

    def __init__(self, connection, current_user: dict) -> None:
        if current_user["role"] not in {"librarian", "admin"}:
            raise PermissionError(
                "LibrarianController can only be instantiated by librarians or admins."
            )
        self.current_user = current_user
        self.user_model   = UserModel(connection)
        self.review_model = ReviewModel(connection)
        self.catalog      = CatalogController(connection, current_user)
        self.submissions  = SubmissionController(connection, current_user)

    @property
    def _user_id(self) -> int:
        return self.current_user["user_id"]

    @property
    def _role(self) -> str:
        return self.current_user["role"]

    def _is_admin(self) -> bool:
        return self._role == "admin"

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard_summary(self) -> dict:
        """
        Return a single-call aggregated dashboard snapshot.

        Optimised: user counts are fetched via one GROUP BY query instead
        of four separate ``SELECT *`` queries.

        Returns:
            dict: ``{"success": bool, "summary": dict}``
        """
        try:
            submission_counts = self.submissions.get_submission_summary().get("counts", {})
            pending_reviews   = self.review_model.get_pending_reviews()
            all_books         = self.catalog.book_model.get_all_books()
            user_counts       = self.user_model.get_user_counts_by_role()

            summary = {
                "pending_submissions":  submission_counts.get("pending", 0),
                "approved_submissions": submission_counts.get("approved", 0),
                "rejected_submissions": submission_counts.get("rejected", 0),
                "pending_reviews":      len(pending_reviews),
                "total_books":          len(all_books),
                "total_users":          sum(user_counts.values()),
                "total_patrons":        user_counts.get("patron", 0),
                "total_contributors":   user_counts.get("contributor", 0),
                "total_librarians":     user_counts.get("librarian", 0),
            }
            return {"success": True, "summary": summary}
        except Exception as exc:
            logger.exception("get_dashboard_summary failed.")
            return {"success": False, "message": str(exc), "summary": {}}

    # ------------------------------------------------------------------
    # Submission management
    # ------------------------------------------------------------------

    def get_pending_submissions(self) -> dict:
        """Return all pending submissions with contributor metadata."""
        return self.submissions.get_pending_submissions()

    def approve_and_ingest(
        self,
        submission_id: int,
        format_type: str,
        subject_tags: str,
        review_notes: str | None = None,
    ) -> dict:
        """
        Approve a submission and atomically ingest it into the catalog.

        Args:
            submission_id (int): Target submission.
            format_type (str): Catalog format type for the new book entry.
            subject_tags (str): Comma-separated subject tags.
            review_notes (str | None): Optional librarian notes.

        Returns:
            dict: ``{"success": bool, "message": str,
                     "submission_id": int, "book_id": int | None}``
        """
        return self.submissions.approve_and_ingest(
            submission_id=submission_id,
            format_type=format_type,
            subject_tags=subject_tags,
            review_notes=review_notes,
        )

    def reject_submission(self, submission_id: int, review_notes: str | None = None) -> dict:
        """Reject a pending submission with optional reviewer notes."""
        return self.submissions.reject_submission(
            submission_id=submission_id, review_notes=review_notes
        )

    # ------------------------------------------------------------------
    # Review moderation
    # ------------------------------------------------------------------

    def get_pending_reviews(self) -> dict:
        """Return all unapproved patron reviews."""
        try:
            reviews = self.review_model.get_pending_reviews()
            return {"success": True, "message": f"{len(reviews)} pending review(s).", "reviews": reviews}
        except Exception as exc:
            logger.exception("get_pending_reviews failed.")
            return {"success": False, "message": str(exc), "reviews": []}

    def approve_review(self, review_id: int) -> dict:
        """Approve a patron review."""
        return self.catalog.approve_review(review_id)

    def reject_review(self, review_id: int) -> dict:
        """Reject a patron review."""
        return self.catalog.reject_review(review_id)

    def remove_review(self, review_id: int) -> dict:
        """Permanently delete a patron review."""
        return self.catalog.remove_review(review_id)

    # ------------------------------------------------------------------
    # Catalog management
    # ------------------------------------------------------------------

    def add_book(
        self,
        title: str,
        author: str,
        publication_year: int | None,
        format_type: str,
        subject_tags: str,
        abstract: str,
        file_path: str | None = None,
    ) -> dict:
        """Add a new book directly to the catalog (bypasses submission queue)."""
        return self.catalog.add_book(
            title=title, author=author, publication_year=publication_year,
            format_type=format_type, subject_tags=subject_tags,
            abstract=abstract, file_path=file_path,
        )

    def edit_book(self, book_id: int, **kwargs) -> dict:
        """Update catalog metadata for an existing book."""
        return self.catalog.edit_book(book_id, **kwargs)

    def remove_book(self, book_id: int) -> dict:
        """Permanently remove a book from the catalog."""
        return self.catalog.remove_book(book_id)

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def get_all_patrons(self) -> dict:
        """Return all patron-role accounts."""
        return self._get_users_by_role("patron")

    def get_all_contributors(self) -> dict:
        """Return all contributor-role accounts."""
        return self._get_users_by_role("contributor")

    def get_user_details(self, user_id: int) -> dict:
        """
        Return a single user's profile (password_hash stripped).

        Args:
            user_id (int): Target user's primary key.

        Returns:
            dict: ``{"success": bool, "message": str, "user": dict | None}``
        """
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                return {"success": False, "message": "User not found.", "user": None}
            user.pop("password_hash", None)
            return {"success": True, "message": "User loaded.", "user": user}
        except Exception as exc:
            logger.exception("get_user_details failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc), "user": None}

    def deactivate_user(self, user_id: int) -> dict:
        """
        Soft-delete a user account.  Librarians may only deactivate
        patrons/contributors; admins may deactivate any account (except
        their own).

        Args:
            user_id (int): Target user's primary key.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target:
                return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {
                    "success": False,
                    "message": "Librarians can only deactivate patron or contributor accounts.",
                }
            if user_id == self._user_id:
                return {"success": False, "message": "You cannot deactivate your own account."}
            return self.user_model.deactivate_user(user_id)
        except Exception as exc:
            logger.exception("deactivate_user failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}

    def reactivate_user(self, user_id: int) -> dict:
        """
        Re-enable a deactivated user account.

        Args:
            user_id (int): Target user's primary key.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target:
                return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {
                    "success": False,
                    "message": "Librarians can only reactivate patron or contributor accounts.",
                }
            return self.user_model.update_user(user_id, is_active=True)
        except Exception as exc:
            logger.exception("reactivate_user failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}

    def get_all_users(self, role: str | None = None) -> dict:
        """
        Admin-only: retrieve all accounts, optionally filtered by role.

        Returns:
            dict: ``{"success": bool, "message": str, "users": list[dict]}``
        """
        if not self._is_admin():
            return {"success": False, "message": "Only admins can view all user accounts.", "users": []}
        return self._get_users_by_role(role)

    def promote_user(self, user_id: int, new_role: str) -> dict:
        """
        Admin-only: change a user's role.

        Args:
            user_id (int): Target user (cannot be self).
            new_role (str): Desired new role.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        if not self._is_admin():
            return {"success": False, "message": "Only admins can change user roles."}
        if user_id == self._user_id:
            return {"success": False, "message": "You cannot change your own role."}
        try:
            return self.user_model.update_user(user_id, role=new_role)
        except Exception as exc:
            logger.exception("promote_user failed for user_id=%s.", user_id)
            return {"success": False, "message": str(exc)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_users_by_role(self, role: str | None = None) -> dict:
        """
        Fetch users by role, strip password hashes, and return a standard dict.

        Args:
            role (str | None): Role to filter by, or ``None`` for all.

        Returns:
            dict: ``{"success": bool, "message": str, "users": list[dict]}``
        """
        try:
            users = self.user_model.get_all_users(role=role)
            for u in users:
                u.pop("password_hash", None)
            label = role if role else "all roles"
            return {"success": True, "message": f"{len(users)} user(s) found for {label}.", "users": users}
        except Exception as exc:
            logger.exception("_get_users_by_role failed for role='%s'.", role)
            return {"success": False, "message": str(exc), "users": []}