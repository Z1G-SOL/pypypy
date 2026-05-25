import logging
from typing import Optional
from models.book_model import BookModel, VALID_FORMATS
from models.review_model import ReviewModel
from models.borrow_model import BorrowModel

logger = logging.getLogger(__name__)


class CatalogController:
    def __init__(self, connection, current_user: dict) -> None:
        self.connection = connection
        self.book_model = BookModel(connection)
        self.review_model = ReviewModel(connection)
        self.current_user = current_user

    @property
    def _user_id(self) -> int:
        return self.current_user["user_id"]

    @property
    def _role(self) -> str:
        return self.current_user["role"]

    def _is_privileged(self) -> bool:
        return self._role in {"librarian", "admin"}

    def _require_privileged(self) -> Optional[dict]:
        return None if self._is_privileged() else {"success": False, "message": "Librarians and admins only."}

    def search_catalog(self, keyword=None, publication_year=None, format_type=None, subject_tag=None) -> dict:
        try:
            books = self.book_model.search_books(
                keyword=keyword,
                publication_year=publication_year,
                format_type=format_type,
                subject_tag=subject_tag
            )
            return {"success": True, "message": f"{len(books)} result(s) found.", "books": books, "count": len(books)}
        except Exception as exc:
            logger.exception("search_catalog failed.")
            return {"success": False, "message": str(exc), "books": [], "count": 0}

    def get_book_details(self, book_id: int) -> dict:
        try:
            book = self.book_model.get_book_by_id(book_id)
            if not book:
                return {"success": False, "message": "Resource not found.", "book": None, "reviews": [],
                        "review_count": 0}

            reviews = self.review_model.get_approved_reviews_by_book(book_id)
            rc = self.review_model.get_review_count_by_book(book_id)

            return {"success": True, "message": "Loaded.", "book": book, "reviews": reviews, "review_count": rc}
        except Exception as exc:
            logger.exception("get_book_details failed book_id=%s.", book_id)
            return {"success": False, "message": str(exc), "book": None, "reviews": [], "review_count": 0}

    def process_borrow_request(self, book_id: int) -> dict:
        """Registers a borrow checkout request inside the transaction model tracking."""
        try:
            borrow_model = BorrowModel(self.connection)
            return borrow_model.borrow_book(self._user_id, book_id)
        except Exception as exc:
            logger.exception("Borrow registration processing failure.")
            return {"success": False, "message": f"Engine execution fault: {str(exc)}"}

    def get_filter_options(self) -> dict:
        try:
            return {
                "success": True,
                "tags": self.book_model.get_distinct_tags(),
                "years": self.book_model.get_distinct_years(),
                "formats": sorted(VALID_FORMATS)
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "tags": [], "years": [], "formats": []}

    def add_book(self, title, author, publication_year, format_type, subject_tags, abstract, file_path=None) -> dict:
        denied = self._require_privileged()
        if denied: return {**denied, "book_id": None}

        return self.book_model.create_book(
            title=title, author=author, publication_year=publication_year,
            format_type=format_type, subject_tags=subject_tags,
            abstract=abstract, added_by=self._user_id, file_path=file_path
        )

    def edit_book(self, book_id: int, **kwargs) -> dict:
        denied = self._require_privileged()
        if denied: return denied
        return self.book_model.update_book(book_id, **kwargs)

    def remove_book(self, book_id: int) -> dict:
        denied = self._require_privileged()
        if denied: return denied
        return self.book_model.delete_book(book_id)

    # -------------------------------------------------------------------------
    # NEW MODERATION PASS-THROUGHS
    # These resolve the AttributeError when LibrarianController attempts to
    # moderate reviews through self.catalog
    # -------------------------------------------------------------------------

    def approve_review(self, review_id: int) -> dict:
        """Passes administrative review approvals to the Review Model layer."""
        denied = self._require_privileged()
        if denied: return denied
        return self.review_model.approve_review(review_id)

    def reject_review(self, review_id: int) -> dict:
        """Passes administrative review rejections to the Review Model layer."""
        denied = self._require_privileged()
        if denied: return denied
        return self.review_model.reject_review(review_id)