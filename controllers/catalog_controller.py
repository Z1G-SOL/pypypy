"""
Libralex Information System
controllers/catalog_controller.py
"""

from models.book_model import BookModel, VALID_FORMATS
from models.review_model import ReviewModel


class CatalogController:
    def __init__(self, connection, current_user):
        self.book_model   = BookModel(connection)
        self.review_model = ReviewModel(connection)
        self.current_user = current_user

    @property
    def _user_id(self):
        return self.current_user["user_id"]

    @property
    def _role(self):
        return self.current_user["role"]

    def _is_privileged(self):
        return self._role in {"librarian", "admin"}

    def _require_privileged(self):
        if not self._is_privileged():
            return {"success": False, "message": "Access denied. Only librarians and admins can perform this action."}
        return None

    def search_catalog(self, keyword=None, publication_year=None, format_type=None, subject_tag=None):
        try:
            books = self.book_model.search_books(keyword=keyword, publication_year=publication_year,
                                                  format_type=format_type, subject_tag=subject_tag)
            return {"success": True, "message": f"{len(books)} result(s) found.", "books": books, "count": len(books)}
        except Exception as e:
            return {"success": False, "message": str(e), "books": [], "count": 0}

    def get_book_details(self, book_id):
        try:
            book = self.book_model.get_book_by_id(book_id)
            if not book:
                return {"success": False, "message": "Resource not found.", "book": None, "reviews": [], "review_count": 0}
            reviews      = self.review_model.get_approved_reviews_by_book(book_id)
            review_count = self.review_model.get_review_count_by_book(book_id)
            return {"success": True, "message": "Resource loaded.", "book": book, "reviews": reviews, "review_count": review_count}
        except Exception as e:
            return {"success": False, "message": str(e), "book": None, "reviews": [], "review_count": 0}

    def get_filter_options(self):
        try:
            return {"success": True, "tags": self.book_model.get_distinct_tags(),
                    "years": self.book_model.get_distinct_years(), "formats": sorted(VALID_FORMATS)}
        except Exception as e:
            return {"success": False, "message": str(e), "tags": [], "years": [], "formats": []}

    def add_book(self, title, author, publication_year, format_type, subject_tags, abstract, file_path=None):
        denied = self._require_privileged()
        if denied:
            return {**denied, "book_id": None}
        try:
            return self.book_model.create_book(title=title, author=author, publication_year=publication_year,
                                               format_type=format_type, subject_tags=subject_tags,
                                               abstract=abstract, added_by=self._user_id, file_path=file_path)
        except Exception as e:
            return {"success": False, "message": str(e), "book_id": None}

    def edit_book(self, book_id, **kwargs):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.book_model.update_book(book_id, **kwargs)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def remove_book(self, book_id):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.book_model.delete_book(book_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_all_reviews_for_book(self, book_id):
        denied = self._require_privileged()
        if denied:
            return {**denied, "reviews": []}
        try:
            reviews = self.review_model.get_all_reviews_by_book(book_id)
            return {"success": True, "message": f"{len(reviews)} review(s) found.", "reviews": reviews}
        except Exception as e:
            return {"success": False, "message": str(e), "reviews": []}

    def approve_review(self, review_id):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.review_model.approve_review(review_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def reject_review(self, review_id):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.review_model.reject_review(review_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    def remove_review(self, review_id):
        denied = self._require_privileged()
        if denied:
            return denied
        try:
            return self.review_model.delete_review(review_id, requesting_user_id=self._user_id, requesting_role=self._role)
        except Exception as e:
            return {"success": False, "message": str(e)}
