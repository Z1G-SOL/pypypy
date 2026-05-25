"""
Libralex Information System
models/analytics_model.py
"""
import logging
from models.base_model import BaseModel

logger = logging.getLogger(__name__)

class AnalyticsModel(BaseModel):
    def __init__(self, connection) -> None:
        self.conn = connection

    def get_kpi_metrics(self) -> dict:
        """Fetches core database metrics across your live production tables."""
        metrics = {"total_users": 0, "total_books": 0, "pending_reviews": 0, "active_borrows": 0}
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor(dictionary=True)

            # Count system users
            cursor.execute("SELECT COUNT(*) AS count FROM users")
            metrics["total_users"] = cursor.fetchone()["count"]

            # Count catalog items
            cursor.execute("SELECT COUNT(*) AS count FROM books")
            metrics["total_books"] = cursor.fetchone()["count"]

            # Count unapproved user reviews
            cursor.execute("SELECT COUNT(*) AS count FROM reviews WHERE is_approved = FALSE")
            metrics["pending_reviews"] = cursor.fetchone()["count"]

            # Count unreturned items from the book_borrows table
            try:
                cursor.execute("SELECT COUNT(*) AS count FROM book_borrows WHERE due_date IS NOT NULL")
                metrics["active_borrows"] = cursor.fetchone()["count"]
            except Exception:
                # Defaults safely to zero if schema configurations vary slightly
                pass

            return {"success": True, "data": metrics}
        except Exception as exc:
            logger.exception("get_kpi_metrics execution fault.")
            return {"success": False, "message": str(exc), "data": metrics}
        finally:
            if cursor: cursor.close()

    def get_top_books(self, limit: int = 5) -> list:
        """Aggregates book performance ratings across approved user submissions."""
        query = """
            SELECT b.book_id, b.title, b.author, 
                   COUNT(r.review_id) as review_count, 
                   ROUND(AVG(r.rating), 1) as avg_rating
            FROM books b
            JOIN reviews r ON b.book_id = r.book_id
            WHERE r.is_approved = TRUE
            GROUP BY b.book_id
            ORDER BY avg_rating DESC, review_count DESC
            LIMIT %s
        """
        try:
            return self._fetch_all(query, (limit,))
        except Exception as exc:
            logger.exception("get_top_books processing query exception.")
            return []