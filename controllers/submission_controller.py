"""
Libralex Information System
controllers/submission_controller.py

Submission lifecycle. Approve-and-ingest is two-phase with clear
partial-failure messaging if catalog ingestion fails after approval.
"""
import logging
from typing import Optional
from models.submission_model import SubmissionModel
from models.book_model import BookModel

logger = logging.getLogger(__name__)

class SubmissionController:
    def __init__(self, connection, current_user: dict) -> None:
        self.submission_model = SubmissionModel(connection)
        self.book_model       = BookModel(connection)
        self.current_user     = current_user

    @property
    def _user_id(self) -> int:  return self.current_user["user_id"]
    @property
    def _role(self) -> str:     return self.current_user["role"]
    def _is_privileged(self) -> bool:      return self._role in {"librarian", "admin"}
    def _is_contributor_or_above(self) -> bool: return self._role in {"contributor", "librarian", "admin"}

    def _require_privileged(self) -> Optional[dict]:
        return None if self._is_privileged() else {"success": False, "message": "Librarians and admins only."}

    def _require_contributor(self) -> Optional[dict]:
        return None if self._is_contributor_or_above() else {"success": False, "message": "Contributors and above only."}

    def submit_work(self, title, author, abstract, file_path) -> dict:
        denied = self._require_contributor()
        if denied: return {**denied, "submission_id": None}
        return self.submission_model.create_submission(self._user_id, title, author, abstract, file_path)

    def get_my_submissions(self) -> dict:
        denied = self._require_contributor()
        if denied: return {**denied, "submissions": []}
        subs = self.submission_model.get_submissions_by_contributor(self._user_id)
        return {"success": True, "message": f"{len(subs)} submission(s).", "submissions": subs}

    def edit_my_submission(self, submission_id: int, **kwargs) -> dict:
        denied = self._require_contributor()
        if denied: return denied
        return self.submission_model.update_submission(submission_id, self._user_id, **kwargs)

    def delete_my_submission(self, submission_id: int) -> dict:
        denied = self._require_contributor()
        if denied: return denied
        return self.submission_model.delete_submission(submission_id, self._user_id, self._role)

    def get_pending_submissions(self) -> dict:
        denied = self._require_privileged()
        if denied: return {**denied, "submissions": []}
        subs = self.submission_model.get_pending_submissions()
        return {"success": True, "message": f"{len(subs)} pending.", "submissions": subs}

    def get_all_submissions(self, status=None) -> dict:
        denied = self._require_privileged()
        if denied: return {**denied, "submissions": [], "counts": {}}
        subs   = self.submission_model.get_all_submissions(status=status)
        counts = self.submission_model.get_submission_count_by_status()
        return {"success": True, "message": f"{len(subs)} found.", "submissions": subs, "counts": counts}

    def approve_and_ingest(self, submission_id, format_type, subject_tags, review_notes=None) -> dict:
        denied = self._require_privileged()
        if denied: return {**denied, "submission_id": submission_id, "book_id": None}
        try:
            approval = self.submission_model.approve_submission(submission_id, self._user_id, review_notes)
        except Exception as exc:
            return {"success": False, "message": f"Approval failed: {exc}", "submission_id": submission_id, "book_id": None}
        if not approval["success"]: return {**approval, "submission_id": submission_id, "book_id": None}
        sub = approval["submission"]
        try:
            ingestion = self.book_model.create_book(title=sub["title"], author=sub["author"],
                                                     publication_year=None, format_type=format_type,
                                                     subject_tags=subject_tags, abstract=sub["abstract"],
                                                     added_by=self._user_id, file_path=sub["file_path"])
        except Exception as exc:
            return {"success": False,
                    "message": f"Approved but catalog ingestion failed: {exc}. Add book manually.",
                    "submission_id": submission_id, "book_id": None}
        if not ingestion["success"]:
            return {"success": False,
                    "message": f"Approved but catalog ingestion failed: {ingestion['message']}. Add book manually.",
                    "submission_id": submission_id, "book_id": None}
        return {"success": True,
                "message": f"Approved and ingested as '{sub['title']}' (Book ID: {ingestion['book_id']}).",
                "submission_id": submission_id, "book_id": ingestion["book_id"]}

    def reject_submission(self, submission_id, review_notes=None) -> dict:
        denied = self._require_privileged()
        if denied: return denied
        return self.submission_model.reject_submission(submission_id, self._user_id, review_notes)

    def get_submission_summary(self) -> dict:
        denied = self._require_privileged()
        if denied: return {**denied, "counts": {}}
        return {"success": True, "counts": self.submission_model.get_submission_count_by_status()}