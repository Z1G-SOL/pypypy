"""
Libralex Information System
models/book_model.py

Handles all persistence operations for the ``books`` catalog table.
"""

import logging
from datetime import datetime

from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_FORMATS: frozenset[str] = frozenset(
    {"e-book", "print", "thesis", "research paper", "other"}
)


class BookModel(BaseModel):
    """
    Data-access object for the ``books`` table.

    Args:
        connection: An active ``mysql.connector`` connection handle.
    """

    def __init__(self, connection) -> None:
        self.conn = connection

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_book(
        self,
        title: str,
        author: str,
        publication_year: int | None,
        format_type: str,
        subject_tags: str | None,
        abstract: str | None,
        added_by: int,
        file_path: str | None = None,
    ) -> dict:
        """
        Insert a new catalog entry.

        Args:
            title (str): Book/resource title.
            author (str): Author name(s).
            publication_year (int | None): Year of publication.
            format_type (str): One of ``VALID_FORMATS``.
            subject_tags (str | None): Comma-separated tags.
            abstract (str | None): Short descriptive summary.
            added_by (int): ``user_id`` of the librarian adding the entry.
            file_path (str | None): Optional path to an attached file.

        Returns:
            dict: ``{"success": bool, "message": str, "book_id": int | None}``
        """
        if not title or not title.strip():
            return {"success": False, "message": "Title cannot be empty.", "book_id": None}
        if not author or not author.strip():
            return {"success": False, "message": "Author cannot be empty.", "book_id": None}

        fmt = format_type.lower().strip() if format_type else ""
        if fmt not in VALID_FORMATS:
            return {
                "success": False,
                "message": f"Invalid format '{fmt}'. Must be one of: {sorted(VALID_FORMATS)}",
                "book_id": None,
            }

        sql = """
            INSERT INTO books
                (title, author, publication_year, format_type, subject_tags,
                 abstract, file_path, added_by, date_added)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            title.strip(), author.strip(), publication_year, fmt,
            subject_tags.strip() if subject_tags else None,
            abstract.strip() if abstract else None,
            file_path.strip() if file_path else None,
            added_by, datetime.now(),
        )
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("Book '%s' created (id=%s) by user_id=%s.", title, new_id, added_by)
            return {"success": True, "message": "Book added to catalog successfully.", "book_id": new_id}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("create_book failed for title='%s'.", title)
            return {"success": False, "message": str(exc), "book_id": None}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_book_by_id(self, book_id: int) -> dict | None:
        """Return the book row for *book_id*, or ``None``."""
        return self._fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))

    def get_all_books(self) -> list[dict]:
        """Return all catalog entries ordered by most recently added."""
        return self._fetch_all("SELECT * FROM books ORDER BY date_added DESC")

    def search_books(
        self,
        keyword: str | None = None,
        publication_year: int | None = None,
        format_type: str | None = None,
        subject_tag: str | None = None,
    ) -> list[dict]:
        """
        Dynamic full-text-style search across catalog entries.

        All parameters are optional and ANDed together.

        Args:
            keyword (str | None): Substring matched against title, author, abstract.
            publication_year (int | None): Exact year filter.
            format_type (str | None): Exact format filter.
            subject_tag (str | None): Substring matched against subject_tags.

        Returns:
            list[dict]: Matching book rows ordered by ``date_added`` descending.
        """
        conditions: list[str] = []
        params: list = []

        if keyword and keyword.strip():
            conditions.append("(title LIKE %s OR author LIKE %s OR abstract LIKE %s)")
            kw = f"%{keyword.strip()}%"
            params.extend([kw, kw, kw])
        if publication_year is not None:
            conditions.append("publication_year = %s")
            params.append(publication_year)
        if format_type and format_type.strip():
            conditions.append("format_type = %s")
            params.append(format_type.lower().strip())
        if subject_tag and subject_tag.strip():
            conditions.append("subject_tags LIKE %s")
            params.append(f"%{subject_tag.strip()}%")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM books {where_clause} ORDER BY date_added DESC"
        return self._fetch_all(sql, tuple(params))

    def get_books_by_format(self, format_type: str) -> list[dict]:
        """Return all books of a given *format_type*."""
        return self._fetch_all(
            "SELECT * FROM books WHERE format_type = %s ORDER BY date_added DESC",
            (format_type.lower().strip(),),
        )

    def get_books_by_year(self, publication_year: int) -> list[dict]:
        """Return all books published in *publication_year*."""
        return self._fetch_all(
            "SELECT * FROM books WHERE publication_year = %s ORDER BY title ASC",
            (publication_year,),
        )

    def get_books_added_by(self, librarian_id: int) -> list[dict]:
        """Return all books catalogued by the librarian with *librarian_id*."""
        return self._fetch_all(
            "SELECT * FROM books WHERE added_by = %s ORDER BY date_added DESC",
            (librarian_id,),
        )

    def get_distinct_tags(self) -> list[str]:
        """
        Return a sorted list of all unique subject tags across the catalog.

        Tags are stored comma-separated in a single column; this method
        splits and deduplicates them in Python.

        Returns:
            list[str]: Sorted unique tag strings.
        """
        rows = self._fetch_all(
            "SELECT subject_tags FROM books WHERE subject_tags IS NOT NULL"
        )
        tag_set: set[str] = set()
        for row in rows:
            for tag in row["subject_tags"].split(","):
                stripped = tag.strip()
                if stripped:
                    tag_set.add(stripped)
        return sorted(tag_set)

    def get_distinct_years(self) -> list[int]:
        """Return distinct publication years present in the catalog, newest first."""
        rows = self._fetch_all(
            "SELECT DISTINCT publication_year FROM books "
            "WHERE publication_year IS NOT NULL ORDER BY publication_year DESC"
        )
        return [row["publication_year"] for row in rows]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_book(self, book_id: int, **kwargs) -> dict:
        """
        Update one or more allowed fields on a book record.

        Args:
            book_id (int): Target book's primary key.
            **kwargs: Field-value pairs. Allowed: ``title``, ``author``,
                      ``publication_year``, ``format_type``, ``subject_tags``,
                      ``abstract``, ``file_path``.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        allowed_fields = {
            "title", "author", "publication_year", "format_type",
            "subject_tags", "abstract", "file_path",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "format_type" in updates:
            fmt = updates["format_type"].lower().strip()
            if fmt not in VALID_FORMATS:
                return {
                    "success": False,
                    "message": f"Invalid format. Must be one of: {sorted(VALID_FORMATS)}",
                }
            updates["format_type"] = fmt

        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE books SET {set_clause} WHERE book_id = %s"
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, list(updates.values()) + [book_id])
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Book not found."}
            return {"success": True, "message": "Book updated successfully."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("update_book failed for book_id=%s.", book_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_book(self, book_id: int) -> dict:
        """
        Remove a book from the catalog.

        Args:
            book_id (int): Target book's primary key.

        Returns:
            dict: ``{"success": bool, "message": str}``
        """
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Book not found."}
            logger.warning("Book id=%s permanently deleted from catalog.", book_id)
            return {"success": True, "message": "Book deleted from catalog."}
        except Exception as exc:
            self.conn.rollback()
            logger.exception("delete_book failed for book_id=%s.", book_id)
            return {"success": False, "message": str(exc)}
        finally:
            if cursor is not None:
                cursor.close()