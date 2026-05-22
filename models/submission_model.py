"""
Libralex Information System
models/submission_model.py

DAL for the submissions table.
Binary magic-byte file validation (PDF + DOCX).
Atomic optimistic approval guard: WHERE status='pending' prevents
double-approval race conditions.
"""
import logging, os
from datetime import datetime
from typing import Optional
from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_STATUSES:        frozenset = frozenset({"pending", "approved", "rejected"})
VALID_FILE_EXTENSIONS: frozenset = frozenset({".pdf", ".docx"})
_MAGIC: dict = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}

def _validate_file(file_path: str) -> Optional[str]:
    _, raw_ext = os.path.splitext(file_path.strip())
    ext = raw_ext.lower()
    if ext not in VALID_FILE_EXTENSIONS:
        return f"Invalid file type '{raw_ext or '(none)'}'. Only PDF and DOCX are accepted."
    if not os.path.isfile(file_path):
        return None  # existence check is caller's responsibility
    try:
        with open(file_path, "rb") as fh:
            header = fh.read(8)
        if not header.startswith(_MAGIC[ext]):
            return f"File content does not match declared type '{ext}'. Only genuine PDF/DOCX files accepted."
    except OSError as exc:
        logger.warning("Could not read file for magic-byte check: %s", exc)
    return None

class SubmissionModel(BaseModel):
    def __init__(self, connection) -> None:
        self.conn = connection

    def create_submission(self, submitted_by, title, author, abstract, file_path) -> dict:
        for name, val in (("Title", title), ("Author", author), ("Abstract", abstract), ("File", file_path)):
            if not val or not str(val).strip():
                return {"success": False, "message": f"{name} cannot be empty.", "submission_id": None}
        err = _validate_file(file_path.strip())
        if err: return {"success": False, "message": err, "submission_id": None}
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO submissions (submitted_by,title,author,abstract,file_path,status,date_submitted) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (submitted_by, title.strip(), author.strip(), abstract.strip(), file_path.strip(), "pending", datetime.now()))
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("Submission id=%s created by user_id=%s.", new_id, submitted_by)
            return {"success": True, "message": "Submission received. Pending librarian review.", "submission_id": new_id}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            logger.exception("create_submission failed user_id=%s.", submitted_by)
            return {"success": False, "message": str(exc), "submission_id": None}
        finally:
            if cursor: cursor.close()

    def get_submission_by_id(self, submission_id: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM submissions WHERE submission_id = %s", (submission_id,))

    def get_submissions_by_contributor(self, user_id: int) -> list:
        return self._fetch_all("SELECT * FROM submissions WHERE submitted_by=%s ORDER BY date_submitted DESC", (user_id,))

    def get_pending_submissions(self) -> list:
        return self._fetch_all(
            "SELECT s.*, u.username, u.full_name AS contributor_name FROM submissions s "
            "JOIN users u ON s.submitted_by=u.user_id WHERE s.status='pending' ORDER BY s.date_submitted ASC")

    def get_all_submissions(self, status: Optional[str] = None) -> list:
        base = ("SELECT s.*, u.username, u.full_name AS contributor_name FROM submissions s "
                "JOIN users u ON s.submitted_by=u.user_id")
        if status:
            sc = status.lower().strip()
            if sc not in VALID_STATUSES: raise ValueError(f"Invalid status '{sc}'.")
            return self._fetch_all(base + " WHERE s.status=%s ORDER BY s.date_submitted DESC", (sc,))
        return self._fetch_all(base + " ORDER BY s.date_submitted DESC")

    def get_submission_count_by_status(self) -> dict:
        rows   = self._fetch_all("SELECT status, COUNT(*) AS cnt FROM submissions GROUP BY status")
        counts = {s: 0 for s in VALID_STATUSES}
        for row in rows: counts[row["status"]] = row["cnt"]
        return counts

    def approve_submission(self, submission_id, reviewed_by, review_notes=None) -> dict:
        return self._update_status(submission_id, "approved", reviewed_by, review_notes)

    def reject_submission(self, submission_id, reviewed_by, review_notes=None) -> dict:
        return self._update_status(submission_id, "rejected", reviewed_by, review_notes)

    def update_submission(self, submission_id: int, submitted_by: int, **kwargs) -> dict:
        sub = self.get_submission_by_id(submission_id)
        if not sub: return {"success": False, "message": "Submission not found."}
        if sub["submitted_by"] != submitted_by: return {"success": False, "message": "You can only edit your own submissions."}
        if sub["status"] != "pending": return {"success": False, "message": f"Cannot edit a {sub['status']} submission."}
        allowed  = {"title", "author", "abstract", "file_path"}
        updates  = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates: return {"success": False, "message": "No valid fields provided."}
        if "file_path" in updates:
            err = _validate_file(updates["file_path"])
            if err: return {"success": False, "message": err}
        set_clause = ", ".join(f"{f} = %s" for f in updates)
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(f"UPDATE submissions SET {set_clause} WHERE submission_id=%s", list(updates.values()) + [submission_id])
            self.conn.commit()
            return {"success": True, "message": "Submission updated."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def delete_submission(self, submission_id: int, requesting_user_id: int, requesting_role: str) -> dict:
        sub = self.get_submission_by_id(submission_id)
        if not sub: return {"success": False, "message": "Submission not found."}
        privileged = requesting_role in {"librarian", "admin"}
        owner      = sub["submitted_by"] == requesting_user_id
        if not privileged and not owner: return {"success": False, "message": "Permission denied."}
        if owner and not privileged and sub["status"] != "pending":
            return {"success": False, "message": f"Cannot delete a {sub['status']} submission."}
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM submissions WHERE submission_id=%s", (submission_id,))
            self.conn.commit()
            return {"success": True, "message": "Submission deleted."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def _update_status(self, submission_id, new_status, reviewed_by, review_notes) -> dict:
        """Atomic update — WHERE status='pending' defeats concurrent double-approval."""
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE submissions SET status=%s,reviewed_by=%s,review_notes=%s,date_reviewed=%s "
                "WHERE submission_id=%s AND status='pending'",
                (new_status, reviewed_by, review_notes, datetime.now(), submission_id))
            self.conn.commit()
            if cursor.rowcount == 0:
                existing = self.get_submission_by_id(submission_id)
                if not existing: return {"success": False, "message": "Submission not found.", "submission": None}
                return {"success": False, "message": f"Already '{existing['status']}' — cannot change.", "submission": None}
            updated = self.get_submission_by_id(submission_id)
            logger.info("Submission id=%s set to '%s' by user_id=%s.", submission_id, new_status, reviewed_by)
            return {"success": True, "message": f"Submission {new_status}.", "submission": updated}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc), "submission": None}
        finally:
            if cursor: cursor.close()