"""
Libralex Information System
models/review_model.py

Handles all persistence operations for the ``reviews`` table.
"""

import logging
from datetime import datetime

from models.base_model import BaseModel

logger = logging.getLogger(__name__)


class ReviewModel(BaseModel):
    """
    Data-access object for the ``reviews`` table.

    Args:
        connection: An active ``mysql.connector`` connection handle.
    """

    def __init__(self, connection) -> None:
        self.conn = connection

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_review(self, book_id: int, user_id: int, review_text: str) -> dict:
        """
        Submit a new review for a catalog item (pending approval).

        Args:
            book_id (int): The book being reviewed.
            user_id (int): The patron submitting the review.
            review_text (str): Review body text.

        Returns:
            dict: ``{"success": bool, "message": str, "review_id": int | None}``
        """
        if not review_text or not review_text.strip():
            return {"success": False, "message": "Review text cannot be empty.", "review_id": None}
        if self.get_review_by_user_and_book(user_id, book_id):
            return {
                "success": False,
                "message": "You have already submitted a review for this resource.",
                "review_id": None,
            }
        sql = """
            INSERT INTO reviews (book_id, user_id, review_text, date_posted, is_approved)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (book_id, user_id, review_text.strip(), datetime.now(), False))
            self.conn.commit()
            return {
                "success": True,
                "message": "Review submitted and is pending librarian approval.",
                "review_id": cursor.lastrowid,
            }
        except Exception as exc:
            self.conn.rollback()
            logger.exception("create_review failed for book_id=%s, user_id=%s.", book_id, user_id)
            return {"success": False, "message": str(exc), "review_id": None}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_review_by_id(self, review_id: int) -> dict | None:
        """Return the review row for *review_id*, or ``None``."""
        return self._fetch_one("SELECT * FROM reviews WHERE review_id = %s", (review_id,))

    def get_review_by_user_and_book(self, user_id: int, book_id: int) -> dict | None:
        """Return the review left by *user_id* on *book_id*, or ``None``."""
        return self._fetch_one(
            "SELECT * FROM reviews WHERE user_id = %s AND book_id = %s",
            (user_id, book_id),
        )

    def get_approved_reviews_by_book(self, book_id: int) -> list[dict]:
        """Return all approved reviews for *book_id*, newest first."""
        return self._fetch_all(
            """
            SELECT r.*, u.username, u.full_name
            FROM reviews r JOIN users u ON r.user_id = u.user_id
            WHERE r.book_id = %s AND r.is_approved = TRUE
            ORDER BY r.date_posted DESC
            """,
            (book_id,),
        )

    def get_all_reviews_by_book(self, book_id: int) -> list[dict]:
        """Return all reviews (approved and pending) for *book_id*."""
        return self._fetch_all(
            """
            SELECT r.*, u.username, u.full_name
            FROM reviews r JOIN users u ON r.user_id = u.user_id
            WHERE r.book_id = %s ORDER BY r.date_posted DESC
            """,
            (book_id,),
        )

    def get_reviews_by_user(self, user_id: int) -> list[dict]:
        """Return all reviews submitted by *user_id*, newest first."""
        return self._fetch_all(
            """
            SELECT r.*, b.title AS book_title
            FROM reviews r JOIN books b ON r.book_id = b.book_id
            WHERE r.user_id = %s ORDER BY r.date_posted DESC
            """,
            (user_id,),
        )

    def get_pending_reviews(self) -> list[dict]:
        """Return all unapproved reviews, oldest first (FIFO moderation queue)."""
        return self._fetch_all(
            """
            SELECT r.*, u.username, u.full_name, b.title AS book_title
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN books b ON r.book_id = b.book_id
            WHERE r.is_approved = FALSE ORDER BY r.date_posted ASC
            """
        )

    def get_review_count_by_book(self, book_id: int) -> dict:
        """
        Return the count of approved reviews for *book_id*.

        Returns a consistent dict shape (like all other model methods) rather
        than a bare int, so callers handle a single return type.

        Args:
            book_id (int): The book's primary key.

        Returns:
            dict: ``{"success": bool, "count": int, "message": str}``
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM reviews WHERE book_id = %s AND is_approved = TRUE",
                (book_id,),
            )
            result = cursor.fetchone()
            count = result[0] if result else 0
            return {"success": True, "count": count, "message": f"{count} approved review(s)."}
        except Exception as exc:
            logger.exception("get_review_count_by_book failed for book_id=%s.", book_id)
            return {"success": False, "count": 0, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_review_text(self, review_id: int, user_id: int, new_text: str) -> dict:
        """
        Edit an existing review's text and re-queue it for approval.

        Args:
            review_id (int): The review to update.
            user_id (int): Must match ``review.user_id`` (ownership check).
            new_text (str): Replacement review body.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        if not new_text or not new_text.strip():
            return {"success": False, "message": "Review text cannot be empty."}
        review = self.get_review_by_id(review_id)
        if not review:
            return {"success": False, "message": "Review not found."}
        if review["user_id"] != user_id:
            return {"success": False, "message": "You can only edit your own reviews."}
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE reviews SET review_text = %s, is_approved = FALSE WHERE review_id = %s",
                (new_text.strip(), review_id),
            )
            self.conn.commit()
            return {"success": True, "message": "Review updated and re-submitted for approval."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("update_review_text failed for review_id=%s.", review_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    def approve_review(self, review_id: int) -> dict:
        """Approve a pending review."""
        return self._set_approval(review_id, approved=True)

    def reject_review(self, review_id: int) -> dict:
        """Reject (soft-deny) a pending review."""
        return self._set_approval(review_id, approved=False)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_review(
        self, review_id: int, requesting_user_id: int, requesting_role: str
    ) -> dict:
        """
        Delete a review. Owners and privileged users (librarian/admin) may delete.

        Args:
            review_id (int): The review to delete.
            requesting_user_id (int): The acting user's ID.
            requesting_role (str): The acting user's role.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        review = self.get_review_by_id(review_id)
        if not review:
            return {"success": False, "message": "Review not found."}
        is_privileged = requesting_role in {"librarian", "admin"}
        is_owner = review["user_id"] == requesting_user_id
        if not is_privileged and not is_owner:
            return {"success": False, "message": "You do not have permission to delete this review."}
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
            self.conn.commit()
            return {"success": True, "message": "Review deleted successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("delete_review failed for review_id=%s.", review_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _set_approval(self, review_id: int, approved: bool) -> dict:
        """
        Toggle the ``is_approved`` flag on a review.

        Args:
            review_id (int): Target review.
            approved (bool): New approval state.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE reviews SET is_approved = %s WHERE review_id = %s",
                (approved, review_id),
            )
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Review not found."}
            status = "approved" if approved else "rejected"
            return {"success": True, "message": f"Review {status} successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("_set_approval failed for review_id=%s.", review_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()