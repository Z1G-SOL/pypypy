from datetime import datetime, timedelta


class BorrowModel:
    def __init__(self, conn):
        """Initializes the data model with the shared active connection object."""
        self.conn = conn

    def borrow_book(self, user_id: int, book_id: int) -> dict:
        """Creates a check-out request with a 'pending' state awaiting Admin actions."""
        cursor = self.conn.cursor(dictionary=True)
        try:
            # Verify user exists and is active
            cursor.execute("SELECT is_active FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user or not user['is_active']:
                return {"success": False, "message": "Account suspended or record not found."}

            # Verify book exists
            cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
            book = cursor.fetchone()
            if not book:
                return {"success": False, "message": "Selected book does not exist."}

            # Check for existing active or pending checkouts
            cursor.execute(
                "SELECT borrow_id, status FROM book_borrows WHERE user_id = %s AND book_id = %s AND status IN ('pending', 'borrowed')",
                (user_id, book_id)
            )
            existing = cursor.fetchone()
            if existing:
                if existing['status'] == 'pending':
                    return {"success": False, "message": "You already have a pending approval request for this book."}
                return {"success": False, "message": "You currently hold an active checked-out copy of this item."}

            # Insert request as 'pending'
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = """
                INSERT INTO book_borrows (book_id, user_id, borrow_date, due_date, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """
            cursor.execute(insert_query, (book_id, user_id, now_str, now_str))
            self.conn.commit()
            return {"success": True,
                    "message": f"Request submitted! '{book['title']}' is now awaiting librarian approval."}
        except Exception as err:
            self.conn.rollback()
            return {"success": False, "message": f"Transaction failed: {err}"}
        finally:
            cursor.close()

    def get_user_borrows(self, user_id: int) -> list:
        """Fetches pending and active checked out items for a patron."""
        cursor = self.conn.cursor(dictionary=True)
        query = """
            SELECT b.title, b.author, bb.borrow_date, bb.due_date, bb.status 
            FROM book_borrows bb
            INNER JOIN books b ON bb.book_id = b.book_id
            WHERE bb.user_id = %s AND bb.status IN ('pending', 'borrowed')
            ORDER BY bb.status DESC, bb.due_date ASC
        """
        try:
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_all_borrows(self) -> list:
        """Retrieves all rows system-wide including request IDs for administration tracking."""
        cursor = self.conn.cursor(dictionary=True)
        query = """
            SELECT bb.borrow_id, b.title, u.full_name, u.email, bb.borrow_date, bb.due_date, bb.status
            FROM book_borrows bb
            INNER JOIN books b ON bb.book_id = b.book_id
            INNER JOIN users u ON bb.user_id = u.user_id
            WHERE bb.status IN ('pending', 'borrowed')
            ORDER BY bb.status DESC, bb.borrow_date DESC
        """
        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()

    def approve_borrow(self, borrow_id: int, duration_days: int = 14) -> bool:
        """Approves a request, updating status to 'borrowed'."""
        cursor = self.conn.cursor()
        borrow_date = datetime.now()
        due_date = borrow_date + timedelta(days=duration_days)
        query = """
            UPDATE book_borrows 
            SET status = 'borrowed', borrow_date = %s, due_date = %s 
            WHERE borrow_id = %s AND status = 'pending'
        """
        try:
            cursor.execute(query, (borrow_date.strftime('%Y-%m-%d %H:%M:%S'), due_date.strftime('%Y-%m-%d %H:%M:%S'),
                                   borrow_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            self.conn.rollback()
            return False
        finally:
            cursor.close()

    def reject_borrow(self, borrow_id: int) -> bool:
        """Rejects a request by updating its status to 'rejected'."""
        cursor = self.conn.cursor()
        query = "UPDATE book_borrows SET status = 'rejected' WHERE borrow_id = %s AND status = 'pending'"
        try:
            cursor.execute(query, (borrow_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            self.conn.rollback()
            return False
        finally:
            cursor.close()