"""
Libralex Information System
controllers/submission_controller.py
"""

from models.submission_model import SubmissionModel
from models.book_model import BookModel


class SubmissionController:
    def __init__(self, connection, current_user):
        self.submission_model = SubmissionModel(connection)
        self.book_model       = BookModel(connection)
        self.current_user     = current_user

    @property
    def _user_id(self):
        return self.current_user["user_id"]

    @property
    def _role(self):
        return self.current_user["role"]

    def _is_privileged(self):
        return self._role in {"librarian", "admin"}

    def _is_contributor_or_above(self):
        return self._role in {"contributor", "librarian", "admin"}

    def _require_privileged(self):
        if not self._is_privileged():
            return {"success": False, "message": "Access denied. Only librarians and admins can perform this action."}
        return None

    def _require_contributor(self):
        if not self._is_contributor_or_above():
            return {"success": False, "message": "Access denied. Only contributors, librarians, and admins can submit works."}
        return None

    def submit_work(self, title, author, abstract, file_path):
        denied = self._require_contributor()
        if denied:
            return {**denied, "submission_id": None}
        try:
            return self.submission_model.create_submission(
                submitted_by=self._user_id, title=title, author=author,
                abstract=abstract, file_path=file_path)
        except Exception as e:
            return {"success": False, "message": str(e), "submission_id": None}

    def get_my_submissions(self):
        denied = self._require_contributor()
        if denied:
            return {**denied, "submissions": []}
        try:
            submissions = self.submission_model.get_submissions_by_contributor(self._user_id)
            return {"success": True, "message": f"{len(submissions)} submission(s) found.", "submissions": submissions}
        except Exception as e:
            return {"success": False, "message": str(e), "submissions": []}

    def edit_my_submission(self, submission_id, **kwargs):
        denied = self._require_contributor()
        if denied:
            return denied
        try:
            return self.submission_model.update_submission(
                submission_id=submission_id, submitted_by=self._user_id, **kwargs)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def delete_my_submission(self, submission_id):
        denied = self._require_contributor()
        if denied:
            return denied
        try:
            return self.submission_model.delete_submission(
                submission_id=submission_id, requesting_user_id=self._user_id, requesting_role=self._role)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_pending_submissions(self):
        denied = self._require_privileged()
        if denied:
            return {**denied, "submissions": []}
        try:
            submissions = self.submission_model.get_pending_submissions()
            return {"success": True, "message": f"{len(submissions)} pending submission(s).", "submissions": submissions}
        except Exception as e:
            return {"success": False, "message": str(e), "submissions": []}

    def get_all_submissions(self, status=None):
        denied = self._require_privileged()
        if denied:
            return {**denied, "submissions": [], "counts": {}}
        try:
            submissions = self.submission_model.get_all_submissions(status=status)
            counts      = self.submission_model.get_submission_count_by_status()
            return {"success": True, "message": f"{len(submissions)} submission(s) found.",
                    "submissions": submissions, "counts": counts}
        except Exception as e:
            return {"success": False, "message": str(e), "submissions": [], "counts": {}}

    def approve_and_ingest(self, submission_id, format_type, subject_tags, review_notes=None):
        denied = self._require_privileged()
        if denied:
            return {**denied, "submission_id": submission_id, "book_id": None}
        try:
            approval = self.submission_model.approve_submission(
                submission_id=submission_id, reviewed_by=self._user_id, review_notes=review_notes)
        except Exception as e:
            return {"success": False, "message": f"Approval failed: {e}", "submission_id": submission_id, "book_id": None}
        if not approval["success"]:
            return {**approval, "submission_id": submission_id, "book_id": None}
        submission = approval["submission"]
        try:
            ingestion = self.book_model.create_book(
                title=submission["title"], author=submission["author"],
                publication_year=None, format_type=format_type,
                subject_tags=subject_tags, abstract=submission["abstract"],
                added_by=self._user_id, file_path=submission["file_path"])
        except Exception as e:
            return {"success": False,
                    "message": f"Submission approved but catalog ingestion failed: {e}. Please add the book manually.",
                    "submission_id": submission_id, "book_id": None}
        if not ingestion["success"]:
            return {"success": False,
                    "message": f"Submission approved but catalog ingestion failed: {ingestion['message']}",
                    "submission_id": submission_id, "book_id": None}
        return {"success": True,
                "message": f"Submission approved and ingested into the catalog as '{submission['title']}' (Book ID: {ingestion['book_id']}).",
                "submission_id": submission_id, "book_id": ingestion["book_id"]}

    def reject_submission(self, submission_id, review_notes=None):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.submission_model.reject_submission(
                submission_id=submission_id, reviewed_by=self._user_id, review_notes=review_notes)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_submission_details(self, submission_id):
        try:
            submission = self.submission_model.get_submission_by_id(submission_id)
            if not submission:
                return {"success": False, "message": "Submission not found.", "submission": None}
            if not self._is_privileged() and submission["submitted_by"] != self._user_id:
                return {"success": False, "message": "Access denied. You can only view your own submissions.", "submission": None}
            return {"success": True, "message": "Submission loaded.", "submission": submission}
        except Exception as e:
            return {"success": False, "message": str(e), "submission": None}

    def get_submission_summary(self):
        denied = self._require_privileged()
        if denied:
            return {**denied, "counts": {}}
        try:
            counts = self.submission_model.get_submission_count_by_status()
            return {"success": True, "counts": counts}
        except Exception as e:
            return {"success": False, "message": str(e), "counts": {}}
