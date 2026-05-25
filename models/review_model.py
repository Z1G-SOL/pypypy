"""
Libralex Information System
models/review_model.py
"""
import logging
from datetime import datetime
from typing import Optional
from models.base_model import BaseModel

logger = logging.getLogger(__name__)

class ReviewModel(BaseModel):
    def __init__(self, connection) -> None:
        self.conn = connection

    def create_review(self, book_id: int, user_id: int, rating: int, review_text: str) -> dict:
        """Saves a new review complete with an integer rating value. Allows multiple reviews."""
        if not review_text or not review_text.strip():
            return {"success": False, "message": "Review text cannot be empty.", "review_id": None}

        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO reviews (book_id, user_id, rating, review_text, date_posted, is_approved) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (book_id, user_id, rating, review_text.strip(), datetime.now(), False)
            )
            self.conn.commit()
            return {"success": True, "message": "Review submitted — pending approval.", "review_id": cursor.lastrowid}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            logger.exception("create_review failed book_id=%s user_id=%s.", book_id, user_id)
            return {"success": False, "message": str(exc), "review_id": None}
        finally:
            if cursor: cursor.close()

    def get_review_by_id(self, review_id: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM reviews WHERE review_id = %s", (review_id,))

    def get_review_by_user_and_book(self, user_id: int, book_id: int) -> Optional[dict]:
        # Kept this utility method in case you still need to check if a user has reviewed a book
        # for other features (e.g., displaying a badge), but it no longer blocks creation.
        return self._fetch_one("SELECT * FROM reviews WHERE user_id = %s AND book_id = %s", (user_id, book_id))

    def get_approved_reviews_by_book(self, book_id: int) -> list:
        return self._fetch_all(
            "SELECT r.*, u.username, u.full_name FROM reviews r JOIN users u ON r.user_id=u.user_id "
            "WHERE r.book_id=%s AND r.is_approved=TRUE ORDER BY r.date_posted DESC", (book_id,))

    def get_all_reviews_by_book(self, book_id: int) -> list:
        return self._fetch_all(
            "SELECT r.*, u.username, u.full_name FROM reviews r JOIN users u ON r.user_id=u.user_id "
            "WHERE r.book_id=%s ORDER BY r.date_posted DESC", (book_id,))

    def get_pending_reviews(self) -> list:
        return self._fetch_all(
            "SELECT r.*, u.username, u.full_name, b.title AS book_title "
            "FROM reviews r JOIN users u ON r.user_id=u.user_id JOIN books b ON r.book_id=b.book_id "
            "WHERE r.is_approved=FALSE ORDER BY r.date_posted ASC")

    def get_review_count_by_book(self, book_id: int) -> int:
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE book_id=%s AND is_approved=TRUE", (book_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            logger.exception("get_review_count_by_book failed book_id=%s.", book_id)
            return 0
        finally:
            if cursor: cursor.close()

    def approve_review(self, review_id: int) -> dict:
        return self._set_approval(review_id, True)

    def reject_review(self, review_id: int) -> dict:
        return self._set_approval(review_id, False)

    def delete_review(self, review_id: int, requesting_user_id: int, requesting_role: str) -> dict:
        review = self.get_review_by_id(review_id)
        if not review: return {"success": False, "message": "Review not found."}
        if requesting_role not in {"librarian", "admin"} and review["user_id"] != requesting_user_id:
            return {"success": False, "message": "You do not have permission to delete this review."}
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
            self.conn.commit()
            return {"success": True, "message": "Review deleted."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def _set_approval(self, review_id: int, approved: bool) -> dict:
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("UPDATE reviews SET is_approved=%s WHERE review_id=%s", (approved, review_id))
            self.conn.commit()
            if cursor.rowcount == 0: return {"success": False, "message": "Review not found."}
            return {"success": True, "message": f"Review {'approved' if approved else 'rejected'}."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()