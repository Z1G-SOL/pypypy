"""
Libralex Information System
models/submission_model.py
"""

from datetime import datetime

VALID_STATUSES = {"pending", "approved", "rejected"}
VALID_FILE_EXTENSIONS = {".pdf", ".docx"}


class SubmissionModel:
    def __init__(self, connection):
        self.conn = connection

    def create_submission(self, submitted_by, title, author, abstract, file_path):
        if not title or not title.strip():
            return {"success": False, "message": "Title cannot be empty.", "submission_id": None}
        if not author or not author.strip():
            return {"success": False, "message": "Author cannot be empty.", "submission_id": None}
        if not abstract or not abstract.strip():
            return {"success": False, "message": "Abstract cannot be empty.", "submission_id": None}
        if not file_path or not file_path.strip():
            return {"success": False, "message": "A file must be attached.", "submission_id": None}
        ext = "." + file_path.strip().rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext not in VALID_FILE_EXTENSIONS:
            return {"success": False, "message": f"Invalid file type '{ext}'. Only PDF and DOCX are accepted.", "submission_id": None}
        sql = """
            INSERT INTO submissions
                (submitted_by, title, author, abstract, file_path, status, date_submitted)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (submitted_by, title.strip(), author.strip(),
                                 abstract.strip(), file_path.strip(), "pending", datetime.now()))
            self.conn.commit()
            return {"success": True, "message": "Submission received. It is now pending librarian review.", "submission_id": cursor.lastrowid}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e), "submission_id": None}
        finally:
            cursor.close()

    def get_submission_by_id(self, submission_id):
        return self._fetch_one("SELECT * FROM submissions WHERE submission_id = %s", (submission_id,))

    def get_submissions_by_contributor(self, user_id):
        return self._fetch_all("SELECT * FROM submissions WHERE submitted_by = %s ORDER BY date_submitted DESC", (user_id,))

    def get_pending_submissions(self):
        return self._fetch_all("""
            SELECT s.*, u.username, u.full_name AS contributor_name
            FROM submissions s JOIN users u ON s.submitted_by = u.user_id
            WHERE s.status = 'pending' ORDER BY s.date_submitted ASC
        """)

    def get_all_submissions(self, status=None):
        if status:
            status = status.lower().strip()
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'.")
            return self._fetch_all("""
                SELECT s.*, u.username, u.full_name AS contributor_name
                FROM submissions s JOIN users u ON s.submitted_by = u.user_id
                WHERE s.status = %s ORDER BY s.date_submitted DESC
            """, (status,))
        return self._fetch_all("""
            SELECT s.*, u.username, u.full_name AS contributor_name
            FROM submissions s JOIN users u ON s.submitted_by = u.user_id
            ORDER BY s.date_submitted DESC
        """)

    def get_submission_count_by_status(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM submissions GROUP BY status")
            rows = cursor.fetchall()
            counts = {"pending": 0, "approved": 0, "rejected": 0}
            for status, count in rows:
                counts[status] = count
            return counts
        finally:
            cursor.close()

    def approve_submission(self, submission_id, reviewed_by, review_notes=None):
        return self._update_status(submission_id, "approved", reviewed_by, review_notes)

    def reject_submission(self, submission_id, reviewed_by, review_notes=None):
        return self._update_status(submission_id, "rejected", reviewed_by, review_notes)

    def update_submission(self, submission_id, submitted_by, **kwargs):
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found."}
        if submission["submitted_by"] != submitted_by:
            return {"success": False, "message": "You can only edit your own submissions."}
        if submission["status"] != "pending":
            return {"success": False, "message": f"Cannot edit a submission that has already been {submission['status']}."}
        allowed_fields = {"title", "author", "abstract", "file_path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "file_path" in updates:
            fp = updates["file_path"].strip()
            ext = "." + fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
            if ext not in VALID_FILE_EXTENSIONS:
                return {"success": False, "message": f"Invalid file type '{ext}'. Only PDF and DOCX are accepted."}
        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE submissions SET {set_clause} WHERE submission_id = %s"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, list(updates.values()) + [submission_id])
            self.conn.commit()
            return {"success": True, "message": "Submission updated successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def delete_submission(self, submission_id, requesting_user_id, requesting_role):
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found."}
        is_privileged = requesting_role in {"librarian", "admin"}
        is_owner = submission["submitted_by"] == requesting_user_id
        if not is_privileged and not is_owner:
            return {"success": False, "message": "You do not have permission to delete this submission."}
        if is_owner and not is_privileged and submission["status"] != "pending":
            return {"success": False, "message": f"Cannot delete a submission that has already been {submission['status']}."}
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM submissions WHERE submission_id = %s", (submission_id,))
            self.conn.commit()
            return {"success": True, "message": "Submission deleted successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def _update_status(self, submission_id, new_status, reviewed_by, review_notes=None):
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return {"success": False, "message": "Submission not found.", "submission": None}
        if submission["status"] != "pending":
            return {"success": False, "message": f"Submission is already {submission['status']}.", "submission": None}
        sql = "UPDATE submissions SET status = %s, reviewed_by = %s, review_notes = %s, date_reviewed = %s WHERE submission_id = %s"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (new_status, reviewed_by, review_notes, datetime.now(), submission_id))
            self.conn.commit()
            return {"success": True, "message": f"Submission {new_status} successfully.", "submission": self.get_submission_by_id(submission_id)}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e), "submission": None}
        finally:
            cursor.close()

    def _fetch_one(self, sql, params=()):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def _fetch_all(self, sql, params=()):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
