"""
Libralex Information System
models/submission_model.py

Handles all persistence operations for the ``submissions`` table.
"""

import logging
import os
from datetime import datetime

from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_STATUSES: frozenset[str] = frozenset({"pending", "approved", "rejected"})
VALID_FILE_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})


def _validate_file_extension(file_path: str) -> str | None:
    """
    Extract and validate the file extension from *file_path*.

    Args:
        file_path (str): Path or filename string.

    Returns:
        str | None: The lower-case extension (e.g. ``".pdf"``) if valid,
                    or ``None`` if the extension is missing or disallowed.
    """
    _, ext = os.path.splitext(file_path.strip())
    return ext.lower() if ext.lower() in VALID_FILE_EXTENSIONS else None


class SubmissionModel(BaseModel):
    """
    Data-access object for the ``submissions`` table.

    Args:
        connection: An active ``mysql.connector`` connection handle.
    """

    def __init__(self, connection) -> None:
        self.conn = connection

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_submission(
        self,
        submitted_by: int,
        title: str,
        author: str,
        abstract: str,
        file_path: str,
    ) -> dict:
        """
        Record a new contributor submission.

        Args:
            submitted_by (int): ``user_id`` of the contributing user.
            title (str): Submission title.
            author (str): Author name(s).
            abstract (str): Descriptive summary.
            file_path (str): Path to the uploaded file (.pdf or .docx only).

        Returns:
            dict: ``{"success": bool, "message": str, "submission_id": int | None}``
        """
        if not title or not title.strip():
            return {"success": False, "message": "Title cannot be empty.", "submission_id": None}
        if not author or not author.strip():
            return {"success": False, "message": "Author cannot be empty.", "submission_id": None}
        if not abstract or not abstract.strip():
            return {"success": False, "message": "Abstract cannot be empty.", "submission_id": None}
        if not file_path or not file_path.strip():
            return {"success": False, "message": "A file must be attached.", "submission_id": None}

        if _validate_file_extension(file_path) is None:
            _, raw_ext = os.path.splitext(file_path.strip())
            return {
                "success": False,
                "message": (
                    f"Invalid file type '{raw_ext or '(none)'}'. "
                    "Only PDF and DOCX are accepted."
                ),
                "submission_id": None,
            }

        sql = """
            INSERT INTO submissions
                (submitted_by, title, author, abstract, file_path, status, date_submitted)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                sql,
                (
                    submitted_by, title.strip(), author.strip(),
                    abstract.strip(), file_path.strip(), "pending", datetime.now(),
                ),
            )
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("Submission id=%s created by user_id=%s.", new_id, submitted_by)
            return {
                "success": True,
                "message": "Submission received. It is now pending librarian review.",
                "submission_id": new_id,
            }
        except Exception as exc:
            self.conn.rollback()
            logger.exception("create_submission failed for user_id=%s.", submitted_by)
            return {"success": False, "message": str(exc), "submission_id": None}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_submission_by_id(self, submission_id: int) -> dict | None:
        """Return the submission row for *submission_id*, or ``None``."""
        return self._fetch_one(
            "SELECT * FROM submissions WHERE submission_id = %s", (submission_id,)
        )

    def get_submissions_by_contributor(self, user_id: int) -> list[dict]:
        """Return all submissions from *user_id*, newest first."""
        return self._fetch_all(
            "SELECT * FROM submissions WHERE submitted_by = %s ORDER BY date_submitted DESC",
            (user_id,),
        )

    def get_pending_submissions(self) -> list[dict]:
        """Return all pending submissions with contributor info, oldest first."""
        return self._fetch_all(
            """
            SELECT s.*, u.username, u.full_name AS contributor_name
            FROM submissions s JOIN users u ON s.submitted_by = u.user_id
            WHERE s.status = 'pending' ORDER BY s.date_submitted ASC
            """
        )

    def get_all_submissions(self, status: str | None = None) -> list[dict]:
        """
        Return all submissions, optionally filtered by *status*.

        Args:
            status (str | None): One of ``VALID_STATUSES``, or ``None`` for all.

        Returns:
            list[dict]: Submission rows joined with contributor username/name.

        Raises:
            ValueError: If *status* is provided but not in ``VALID_STATUSES``.
        """
        base_sql = """
            SELECT s.*, u.username, u.full_name AS contributor_name
            FROM submissions s JOIN users u ON s.submitted_by = u.user_id
        """
        if status:
            status = status.lower().strip()
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'. Must be one of: {sorted(VALID_STATUSES)}")
            return self._fetch_all(
                base_sql + " WHERE s.status = %s ORDER BY s.date_submitted DESC", (status,)
            )
        return self._fetch_all(base_sql + " ORDER BY s.date_submitted DESC")

    def get_submission_count_by_status(self) -> dict[str, int]:
        """
        Return submission counts grouped by status in a single DB round-trip.

        Returns:
            dict[str, int]: ``{"pending": N, "approved": N, "rejected": N}``
        """
        rows = self._fetch_all("SELECT status, COUNT(*) AS cnt FROM submissions GROUP BY status")
        counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
        for row in rows:
            counts[row["status"]] = row["cnt"]
        return counts

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def approve_submission(
        self, submission_id: int, reviewed_by: int, review_notes: str | None = None
    ) -> dict:
        """Approve a pending submission."""
        return self._update_status(submission_id, "approved", reviewed_by, review_notes)

    def reject_submission(
        self, submission_id: int, reviewed_by: int, review_notes: str | None = None
    ) -> dict:
        """Reject a pending submission."""
        return self._update_status(submission_id, "rejected", reviewed_by, review_notes)

    def update_submission(self, submission_id: int, submitted_by: int, **kwargs) -> dict:
        """
        Edit a pending submission's metadata. Only the submitter may edit,
        and only while the submission is in ``pending`` status.

        Args:
            submission_id (int): Target submission.
            submitted_by (int): Must match ``submission.submitted_by``.
            **kwargs: Field-value pairs. Allowed: ``title``, ``author``,
                      ``abstract``, ``file_path``.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found."}
        if submission["submitted_by"] != submitted_by:
            return {"success": False, "message": "You can only edit your own submissions."}
        if submission["status"] != "pending":
            return {
                "success": False,
                "message": f"Cannot edit a submission that has already been {submission['status']}.",
            }
        allowed_fields = {"title", "author", "abstract", "file_path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "file_path" in updates:
            if _validate_file_extension(updates["file_path"]) is None:
                _, raw_ext = os.path.splitext(updates["file_path"].strip())
                return {
                    "success": False,
                    "message": f"Invalid file type '{raw_ext or '(none)'}'. Only PDF and DOCX are accepted.",
                }

        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE submissions SET {set_clause} WHERE submission_id = %s"
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, list(updates.values()) + [submission_id])
            self.conn.commit()
            return {"success": True, "message": "Submission updated successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("update_submission failed for submission_id=%s.", submission_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_submission(
        self, submission_id: int, requesting_user_id: int, requesting_role: str
    ) -> dict:
        """
        Delete a submission. Privileged users may always delete; owners may
        only delete their own submissions while they remain ``pending``.

        Args:
            submission_id (int): Target submission.
            requesting_user_id (int): The acting user's ID.
            requesting_role (str): The acting user's role.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found."}
        is_privileged = requesting_role in {"librarian", "admin"}
        is_owner = submission["submitted_by"] == requesting_user_id
        if not is_privileged and not is_owner:
            return {"success": False, "message": "You do not have permission to delete this submission."}
        if is_owner and not is_privileged and submission["status"] != "pending":
            return {
                "success": False,
                "message": f"Cannot delete a submission that has already been {submission['status']}.",
            }
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM submissions WHERE submission_id = %s", (submission_id,))
            self.conn.commit()
            logger.info("Submission id=%s deleted by user_id=%s.", submission_id, requesting_user_id)
            return {"success": True, "message": "Submission deleted successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("delete_submission failed for submission_id=%s.", submission_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _update_status(
        self,
        submission_id: int,
        new_status: str,
        reviewed_by: int,
        review_notes: str | None,
    ) -> dict:
        """
        Atomically update a submission's status, reviewer, notes, and timestamp.

        Args:
            submission_id (int): Target submission.
            new_status (str): ``"approved"`` or ``"rejected"``.
            reviewed_by (int): ``user_id`` of the reviewer.
            review_notes (str | None): Optional librarian notes.

        Returns:
            dict: ``{"success": bool, "message": str, "submission": dict | None}``
        """
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found.", "submission": None}
        if submission["status"] != "pending":
            return {
                "success": False,
                "message": f"Submission is already {submission['status']}.",
                "submission": None,
            }
        sql = """
            UPDATE submissions
            SET status = %s, reviewed_by = %s, review_notes = %s, date_reviewed = %s
            WHERE submission_id = %s
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (new_status, reviewed_by, review_notes, datetime.now(), submission_id))
            self.conn.commit()
            updated = self.get_submission_by_id(submission_id)
            logger.info(
                "Submission id=%s set to '%s' by user_id=%s.",
                submission_id, new_status, reviewed_by,
            )
            return {
                "success": True,
                "message": f"Submission {new_status} successfully.",
                "submission": updated,
            }
        except Exception as exc:
            self.conn.rollback()
            logger.exception("_update_status failed for submission_id=%s.", submission_id)
            return {"success": False, "message": str(exc), "submission": None}
        finally:
            if cursor is not None:
                cursor.close()