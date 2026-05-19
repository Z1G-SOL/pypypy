"""
Libralex Information System
models/review_model.py
"""

from datetime import datetime


class ReviewModel:
    def __init__(self, connection):
        self.conn = connection

    def create_review(self, book_id, user_id, review_text):
        if not review_text or not review_text.strip():
            return {"success": False, "message": "Review text cannot be empty.", "review_id": None}
        if self.get_review_by_user_and_book(user_id, book_id):
            return {"success": False, "message": "You have already submitted a review for this resource.", "review_id": None}
        sql = "INSERT INTO reviews (book_id, user_id, review_text, date_posted, is_approved) VALUES (%s, %s, %s, %s, %s)"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, (book_id, user_id, review_text.strip(), datetime.now(), False))
            self.conn.commit()
            return {"success": True, "message": "Review submitted and is pending librarian approval.", "review_id": cursor.lastrowid}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e), "review_id": None}
        finally:
            cursor.close()

    def get_review_by_id(self, review_id):
        return self._fetch_one("SELECT * FROM reviews WHERE review_id = %s", (review_id,))

    def get_review_by_user_and_book(self, user_id, book_id):
        return self._fetch_one("SELECT * FROM reviews WHERE user_id = %s AND book_id = %s", (user_id, book_id))

    def get_approved_reviews_by_book(self, book_id):
        return self._fetch_all("""
            SELECT r.*, u.username, u.full_name
            FROM reviews r JOIN users u ON r.user_id = u.user_id
            WHERE r.book_id = %s AND r.is_approved = TRUE
            ORDER BY r.date_posted DESC
        """, (book_id,))

    def get_all_reviews_by_book(self, book_id):
        return self._fetch_all("""
            SELECT r.*, u.username, u.full_name
            FROM reviews r JOIN users u ON r.user_id = u.user_id
            WHERE r.book_id = %s ORDER BY r.date_posted DESC
        """, (book_id,))

    def get_reviews_by_user(self, user_id):
        return self._fetch_all("""
            SELECT r.*, b.title AS book_title
            FROM reviews r JOIN books b ON r.book_id = b.book_id
            WHERE r.user_id = %s ORDER BY r.date_posted DESC
        """, (user_id,))

    def get_pending_reviews(self):
        return self._fetch_all("""
            SELECT r.*, u.username, u.full_name, b.title AS book_title
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            JOIN books b ON r.book_id = b.book_id
            WHERE r.is_approved = FALSE ORDER BY r.date_posted ASC
        """)

    def get_review_count_by_book(self, book_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE book_id = %s AND is_approved = TRUE", (book_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()

    def approve_review(self, review_id):
        return self._set_approval(review_id, True)

    def reject_review(self, review_id):
        return self._set_approval(review_id, False)

    def update_review_text(self, review_id, user_id, new_text):
        if not new_text or not new_text.strip():
            return {"success": False, "message": "Review text cannot be empty."}
        review = self.get_review_by_id(review_id)
        if not review:
            return {"success": False, "message": "Review not found."}
        if review["user_id"] != user_id:
            return {"success": False, "message": "You can only edit your own reviews."}
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE reviews SET review_text = %s, is_approved = FALSE WHERE review_id = %s",
                           (new_text.strip(), review_id))
            self.conn.commit()
            return {"success": True, "message": "Review updated and re-submitted for approval."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def delete_review(self, review_id, requesting_user_id, requesting_role):
        review = self.get_review_by_id(review_id)
        if not review:
            return {"success": False, "message": "Review not found."}
        is_privileged = requesting_role in {"librarian", "admin"}
        is_owner = review["user_id"] == requesting_user_id
        if not is_privileged and not is_owner:
            return {"success": False, "message": "You do not have permission to delete this review."}
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
            self.conn.commit()
            return {"success": True, "message": "Review deleted successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def _set_approval(self, review_id, approved):
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE reviews SET is_approved = %s WHERE review_id = %s", (approved, review_id))
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Review not found."}
            status = "approved" if approved else "rejected"
            return {"success": True, "message": f"Review {status} successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
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
