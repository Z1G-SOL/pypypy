"""
Libralex Information System
controllers/librarian_controller.py
"""

from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from models.user_model import UserModel
from models.review_model import ReviewModel


class LibrarianController:
    def __init__(self, connection, current_user):
        if current_user["role"] not in {"librarian", "admin"}:
            raise PermissionError("LibrarianController can only be instantiated by librarians or admins.")
        self.current_user = current_user
        self.user_model   = UserModel(connection)
        self.review_model = ReviewModel(connection)
        self.catalog      = CatalogController(connection, current_user)
        self.submissions  = SubmissionController(connection, current_user)

    @property
    def _user_id(self):
        return self.current_user["user_id"]

    @property
    def _role(self):
        return self.current_user["role"]

    def _is_admin(self):
        return self._role == "admin"

    def get_dashboard_summary(self):
        try:
            submission_counts = self.submissions.get_submission_summary()["counts"]
            pending_reviews   = self.review_model.get_pending_reviews()
            all_books         = self.catalog.book_model.get_all_books()
            all_users         = self.user_model.get_all_users()
            summary = {
                "pending_submissions":  submission_counts.get("pending", 0),
                "approved_submissions": submission_counts.get("approved", 0),
                "rejected_submissions": submission_counts.get("rejected", 0),
                "pending_reviews":      len(pending_reviews),
                "total_books":          len(all_books),
                "total_users":          len(all_users),
                "total_patrons":        len(self.user_model.get_all_users(role="patron")),
                "total_contributors":   len(self.user_model.get_all_users(role="contributor")),
            }
            return {"success": True, "summary": summary}
        except Exception as e:
            return {"success": False, "message": str(e), "summary": {}}

    def get_pending_submissions(self):
        return self.submissions.get_pending_submissions()

    def approve_and_ingest(self, submission_id, format_type, subject_tags, review_notes=None):
        return self.submissions.approve_and_ingest(
            submission_id=submission_id, format_type=format_type,
            subject_tags=subject_tags, review_notes=review_notes)

    def reject_submission(self, submission_id, review_notes=None):
        return self.submissions.reject_submission(submission_id=submission_id, review_notes=review_notes)

    def get_pending_reviews(self):
        try:
            reviews = self.review_model.get_pending_reviews()
            return {"success": True, "message": f"{len(reviews)} pending review(s).", "reviews": reviews}
        except Exception as e:
            return {"success": False, "message": str(e), "reviews": []}

    def approve_review(self, review_id):
        return self.catalog.approve_review(review_id)

    def reject_review(self, review_id):
        return self.catalog.reject_review(review_id)

    def remove_review(self, review_id):
        return self.catalog.remove_review(review_id)

    def add_book(self, title, author, publication_year, format_type, subject_tags, abstract, file_path=None):
        return self.catalog.add_book(title=title, author=author, publication_year=publication_year,
                                     format_type=format_type, subject_tags=subject_tags,
                                     abstract=abstract, file_path=file_path)

    def edit_book(self, book_id, **kwargs):
        return self.catalog.edit_book(book_id, **kwargs)

    def remove_book(self, book_id):
        return self.catalog.remove_book(book_id)

    def get_all_patrons(self):
        return self._get_users_by_role("patron")

    def get_all_contributors(self):
        return self._get_users_by_role("contributor")

    def get_user_details(self, user_id):
        try:
            user = self.user_model.get_user_by_id(user_id)
            if not user:
                return {"success": False, "message": "User not found.", "user": None}
            user.pop("password_hash", None)
            return {"success": True, "message": "User loaded.", "user": user}
        except Exception as e:
            return {"success": False, "message": str(e), "user": None}

    def deactivate_user(self, user_id):
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target:
                return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {"success": False, "message": "Librarians can only deactivate patron or contributor accounts."}
            if user_id == self._user_id:
                return {"success": False, "message": "You cannot deactivate your own account."}
            return self.user_model.deactivate_user(user_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def reactivate_user(self, user_id):
        try:
            target = self.user_model.get_user_by_id(user_id)
            if not target:
                return {"success": False, "message": "User not found."}
            if not self._is_admin() and target["role"] in {"librarian", "admin"}:
                return {"success": False, "message": "Librarians can only reactivate patron or contributor accounts."}
            return self.user_model.update_user(user_id, is_active=True)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_all_users(self, role=None):
        if not self._is_admin():
            return {"success": False, "message": "Only admins can view all user accounts.", "users": []}
        return self._get_users_by_role(role)

    def promote_user(self, user_id, new_role):
        if not self._is_admin():
            return {"success": False, "message": "Only admins can change user roles."}
        if user_id == self._user_id:
            return {"success": False, "message": "You cannot change your own role."}
        try:
            return self.user_model.update_user(user_id, role=new_role)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _get_users_by_role(self, role=None):
        try:
            users = self.user_model.get_all_users(role=role)
            for u in users:
                u.pop("password_hash", None)
            label = role if role else "all roles"
            return {"success": True, "message": f"{len(users)} user(s) found for {label}.", "users": users}
        except Exception as e:
            return {"success": False, "message": str(e), "users": []}
