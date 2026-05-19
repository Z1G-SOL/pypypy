"""
Libralex Information System
models/book_model.py
"""

from datetime import datetime

VALID_FORMATS = {"e-book", "print", "thesis", "research paper", "other"}


class BookModel:
    def __init__(self, connection):
        self.conn = connection

    def create_book(self, title, author, publication_year, format_type,
                    subject_tags, abstract, added_by, file_path=None):
        format_type = format_type.lower().strip()
        if format_type not in VALID_FORMATS:
            raise ValueError(f"Invalid format '{format_type}'. Must be one of: {VALID_FORMATS}")
        if not title or not title.strip():
            return {"success": False, "message": "Title cannot be empty.", "book_id": None}
        if not author or not author.strip():
            return {"success": False, "message": "Author cannot be empty.", "book_id": None}
        sql = """
            INSERT INTO books
                (title, author, publication_year, format_type, subject_tags,
                 abstract, file_path, added_by, date_added)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (title.strip(), author.strip(), publication_year, format_type,
                  subject_tags.strip() if subject_tags else None,
                  abstract.strip() if abstract else None,
                  file_path.strip() if file_path else None,
                  added_by, datetime.now())
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            return {"success": True, "message": "Book added to catalog successfully.", "book_id": cursor.lastrowid}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e), "book_id": None}
        finally:
            cursor.close()

    def get_book_by_id(self, book_id):
        return self._fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))

    def get_all_books(self):
        return self._fetch_all("SELECT * FROM books ORDER BY date_added DESC")

    def search_books(self, keyword=None, publication_year=None, format_type=None, subject_tag=None):
        conditions = []
        params = []
        if keyword and keyword.strip():
            conditions.append("(title LIKE %s OR author LIKE %s OR abstract LIKE %s)")
            kw = f"%{keyword.strip()}%"
            params.extend([kw, kw, kw])
        if publication_year:
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

    def get_books_by_format(self, format_type):
        return self._fetch_all("SELECT * FROM books WHERE format_type = %s ORDER BY date_added DESC",
                               (format_type.lower().strip(),))

    def get_books_by_year(self, publication_year):
        return self._fetch_all("SELECT * FROM books WHERE publication_year = %s ORDER BY title ASC",
                               (publication_year,))

    def get_books_added_by(self, librarian_id):
        return self._fetch_all("SELECT * FROM books WHERE added_by = %s ORDER BY date_added DESC",
                               (librarian_id,))

    def get_distinct_tags(self):
        rows = self._fetch_all("SELECT subject_tags FROM books WHERE subject_tags IS NOT NULL")
        tag_set = set()
        for row in rows:
            for tag in row["subject_tags"].split(","):
                stripped = tag.strip()
                if stripped:
                    tag_set.add(stripped)
        return sorted(tag_set)

    def get_distinct_years(self):
        rows = self._fetch_all(
            "SELECT DISTINCT publication_year FROM books "
            "WHERE publication_year IS NOT NULL ORDER BY publication_year DESC")
        return [row["publication_year"] for row in rows]

    def update_book(self, book_id, **kwargs):
        allowed_fields = {"title", "author", "publication_year", "format_type",
                          "subject_tags", "abstract", "file_path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return {"success": False, "message": "No valid fields provided for update."}
        if "format_type" in updates:
            updates["format_type"] = updates["format_type"].lower().strip()
            if updates["format_type"] not in VALID_FORMATS:
                raise ValueError(f"Invalid format. Must be one of: {VALID_FORMATS}")
        set_clause = ", ".join(f"{field} = %s" for field in updates)
        sql = f"UPDATE books SET {set_clause} WHERE book_id = %s"
        values = list(updates.values()) + [book_id]
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Book not found."}
            return {"success": True, "message": "Book updated successfully."}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            cursor.close()

    def delete_book(self, book_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                return {"success": False, "message": "Book not found."}
            return {"success": True, "message": "Book deleted from catalog."}
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
