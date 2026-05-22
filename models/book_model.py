"""
Libralex Information System
models/book_model.py

DAL for the books catalog table. Parameterised LIKE search, whitelist
format validation, optimistic existence guard on updates.
"""
import logging
from datetime import datetime
from typing import Optional
from models.base_model import BaseModel

logger = logging.getLogger(__name__)

VALID_FORMATS: frozenset = frozenset({"e-book", "print", "thesis", "research paper", "other"})

class BookModel(BaseModel):
    def __init__(self, connection) -> None:
        self.conn = connection

    def create_book(self, title, author, publication_year, format_type,
                    subject_tags, abstract, added_by, file_path=None) -> dict:
        if not title or not title.strip():  return {"success": False, "message": "Title cannot be empty.", "book_id": None}
        if not author or not author.strip(): return {"success": False, "message": "Author cannot be empty.", "book_id": None}
        fmt = format_type.lower().strip() if format_type else ""
        if fmt not in VALID_FORMATS:
            return {"success": False, "message": f"Invalid format '{fmt}'. Must be one of: {sorted(VALID_FORMATS)}.", "book_id": None}
        sql = """INSERT INTO books (title,author,publication_year,format_type,subject_tags,abstract,file_path,added_by,date_added)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(sql, (title.strip(), author.strip(), publication_year, fmt,
                                 subject_tags.strip() if subject_tags else None,
                                 abstract.strip()     if abstract     else None,
                                 file_path.strip()    if file_path    else None,
                                 added_by, datetime.now()))
            self.conn.commit()
            new_id = cursor.lastrowid
            logger.info("Book id=%s added by user_id=%s.", new_id, added_by)
            return {"success": True, "message": "Book added successfully.", "book_id": new_id}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            logger.exception("create_book failed.")
            return {"success": False, "message": str(exc), "book_id": None}
        finally:
            if cursor: cursor.close()

    def get_book_by_id(self, book_id: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))

    def get_all_books(self) -> list:
        return self._fetch_all("SELECT * FROM books ORDER BY date_added DESC")

    def search_books(self, keyword=None, publication_year=None, format_type=None, subject_tag=None) -> list:
        conditions, params = [], []
        if keyword and keyword.strip():
            conditions.append("(title LIKE %s OR author LIKE %s OR abstract LIKE %s)")
            kw = f"%{keyword.strip()}%"
            params.extend([kw, kw, kw])
        if publication_year is not None:
            conditions.append("publication_year = %s"); params.append(publication_year)
        if format_type and format_type.strip():
            fmt = format_type.lower().strip()
            if fmt in VALID_FORMATS:
                conditions.append("format_type = %s"); params.append(fmt)
        if subject_tag and subject_tag.strip():
            conditions.append("subject_tags LIKE %s"); params.append(f"%{subject_tag.strip()}%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self._fetch_all(f"SELECT * FROM books {where} ORDER BY date_added DESC", tuple(params))

    def get_distinct_tags(self) -> list:
        rows    = self._fetch_all("SELECT subject_tags FROM books WHERE subject_tags IS NOT NULL")
        tag_set = set()
        for row in rows:
            for tag in row["subject_tags"].split(","):
                t = tag.strip()
                if t: tag_set.add(t)
        return sorted(tag_set)

    def get_distinct_years(self) -> list:
        rows = self._fetch_all("SELECT DISTINCT publication_year FROM books WHERE publication_year IS NOT NULL ORDER BY publication_year DESC")
        return [row["publication_year"] for row in rows]

    def update_book(self, book_id: int, **kwargs) -> dict:
        allowed = {"title", "author", "publication_year", "format_type", "subject_tags", "abstract", "file_path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates: return {"success": False, "message": "No valid fields provided."}
        if "format_type" in updates:
            fmt = updates["format_type"].lower().strip()
            if fmt not in VALID_FORMATS: return {"success": False, "message": f"Invalid format. Must be one of: {sorted(VALID_FORMATS)}."}
            updates["format_type"] = fmt
        if not self.get_book_by_id(book_id): return {"success": False, "message": "Book not found."}
        set_clause = ", ".join(f"{f} = %s" for f in updates)
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute(f"UPDATE books SET {set_clause} WHERE book_id = %s", list(updates.values()) + [book_id])
            self.conn.commit()
            if cursor.rowcount == 0: return {"success": False, "message": "No changes made."}
            return {"success": True, "message": "Book updated successfully."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()

    def delete_book(self, book_id: int) -> dict:
        cursor = None
        try:
            self._check_conn()
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            self.conn.commit()
            if cursor.rowcount == 0: return {"success": False, "message": "Book not found."}
            logger.warning("Book id=%s deleted.", book_id)
            return {"success": True, "message": "Book deleted."}
        except Exception as exc:
            try: self.conn.rollback()
            except Exception: pass
            return {"success": False, "message": str(exc)}
        finally:
            if cursor: cursor.close()