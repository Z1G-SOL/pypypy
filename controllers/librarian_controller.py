"""
Libralex Information System
controllers/librarian_controller.py

Aggregate controller for the Librarian Dashboard.
Instantiation raises PermissionError for non-librarian/admin users.
"""
import logging
from typing import Optional
from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from models.user_model import UserModel
from models.review_model import ReviewModel

logger = logging.getLogger(__name__)

class LibrarianController:
    def __init__(self, connection, current_user: dict) -> None:
        if current_user["role"] not in {"librarian", "admin"}:
            raise PermissionError("LibrarianController requires librarian or admin role.")
        self.current_user = current_user
        self.user_model   = UserModel(connection)
        self.review_model = ReviewModel(connection)
        self.catalog      = CatalogController(connection, current_user)
        self.submissions  = SubmissionController(connection, current_user)

    @property
    def _user_id(self) -> int:     return self.current_user["user_id"]
    @property
    def _role(self) -> str:        return self.current_user["role"]
    def _is_admin(self) -> bool:   return self._role == "admin"

    def get_dashboard_summary(self) -> dict:
        try:
            sub_counts   = self.submissions.get_submission_summary().get("counts", {})
            pending_revs = self.review_model.get_pending_reviews()
            all_books    = self.catalog.book_model.get_all_books()
            user_counts  = self.user_model.get_user_counts_by_role()
            return {"success": True, "summary": {
                "pending_submissions":  sub_counts.get("pending",  0),
                "approved_submissions": sub_counts.get("approved", 0),
                "rejected_submissions": sub_counts.get("rejected", 0),
                "pending_reviews":      len(pending_revs),
                "total_books":          len(all_books),
                "total_users":          sum(user_counts.values()),
                "total_patrons":        user_counts.get("patron",      0),
                "total_contributors":   user_counts.get("contributor", 0),
                "total_librarians":     user_counts.get("librarian",   0),
            }}
        except Exception as exc:
            logger.exception("get_dashboard_summary failed.")
            return {"success": False, "message": str(exc), "summary": {}}

    def get_pending_submissions(self) -> dict:
        return self.submissions.get_pending_submissions()

    def approve_and_ingest(self, submission_id, format_type, subject_tags, review_notes=None) -> dict:
        return self.submissions.approve_and_ingest(submission_id, format_type, subject_tags, review_notes)

    def reject_submission(self, submission_id, review_notes=None) -> dict:
        return self.submissions.reject_submission(submission_id, review_notes)

    def get_pending_reviews(self) -> dict:
        try:
            reviews = self.review_model.get_pending_reviews()
            return {"success": True, "message": f"{len(reviews)} pending review(s).", "reviews": reviews}
        except Exception as exc:
            return {"success": False, "message": str(exc), "reviews": []}

    def approve_review(self, review_id: int) -> dict: return self.catalog.approve_review(review_id)
    def reject_review(self, review_id: int) -> dict:  return self.catalog.reject_review(review_id)
    def remove_review(self, review_id: int) -> dict:  return self.catalog.remove_review(review_id)

    def add_book(self, title, author, publication_year, format_type, subject_tags, abstract, file_path=None) -> dict:
        return self.catalog.add_book(title=title, author=author, publication_year=publication_year,
                                     format_type=format_type, subject_tags=subject_tags,
                                     abstract=abstract, file_path=file_path)

    def edit_book(self, book_id: int, **kwargs) -> dict:   return self.catalog.edit_book(book_id, **kwargs)
    def remove_book(self, book_id: int) -> dict:           return self.catalog.remove_book(book_id)

    def get_all_patrons(self) -> dict:       return self._get_users("patron")
    def get_all_contributors(self) -> dict:  return self._get_users("contributor")

    def get_all_users(self, role=None) -> dict:
        if not self._is_admin(): return {"success": False, "message": "Admins only.", "users": []}
        return self._get_users(role)

    def deactivate_user(self, user_id: int) -> dict:
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target: return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {"success": False, "message": "Librarians can only deactivate patrons/contributors."}
            if user_id == self._user_id: return {"success": False, "message": "Cannot deactivate your own account."}
            return self.user_model.deactivate_user(user_id)
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def reactivate_user(self, user_id: int) -> dict:
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target: return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {"success": False, "message": "Librarians can only reactivate patrons/contributors."}
            return self.user_model.update_user(user_id, is_active=True)
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def promote_user(self, user_id: int, new_role: str) -> dict:
        if not self._is_admin(): return {"success": False, "message": "Admins only."}
        if user_id == self._user_id: return {"success": False, "message": "Cannot change your own role."}
        return self.user_model.update_user(user_id, role=new_role)

    def _get_users(self, role=None) -> dict:
        try:
            users = self.user_model.get_all_users(role=role)
            for u in users: u.pop("password_hash", None)
            return {"success": True, "message": f"{len(users)} user(s).", "users": users}
        except Exception as exc:
            return {"success": False, "message": str(exc), "users": []}