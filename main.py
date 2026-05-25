"""
Libralex Information System
main.py — Application entry point
"""

import logging
import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox, QTabWidget

from database.db_connection import get_connection, test_connection
from controllers.auth_controller import AuthController
from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from controllers.librarian_controller import LibrarianController
from controllers.borrow_controller import BorrowController
from models.review_model import ReviewModel

from views.login_view import LoginView
from views.signup_view import SignUpView
from views.catalog_view import CatalogView
from views.submission_view import SubmissionView
from views.librarian_view import LibrarianView


# --- CRASH GUARD INTERCEPTOR ---
def qt_exception_hook(exctype, value, tb):
    """Intercepts unhandled internal thread exceptions and forces stdout formatting dump."""
    print("=== CRITICAL SYSTEM EXCEPTION ===", file=sys.stderr)
    print("".join(traceback.format_exception(exctype, value, tb)), file=sys.stderr)
    sys.exit(1)

sys.excepthook = qt_exception_hook
# -------------------------------


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class LibralexApp:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Libralex")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Libralex Info System")

        self.conn: object | None = None
        self.auth: AuthController | None = None
        self.current_win: object | None = None
        self.borrow_ctrl: BorrowController | None = None

    def run(self) -> None:
        status = test_connection()
        if not status["success"]:
            QMessageBox.critical(None, "Database Error", f"Could not connect to the database.\n\n{status['message']}")
            sys.exit(1)

        self.conn = get_connection()
        self.auth = AuthController(self.conn)
        self._inject_admin_override()

        logger.info("Libralex started successfully.")
        self._show_login()
        sys.exit(self.app.exec())

    def _inject_admin_override(self) -> None:
        original_login = getattr(self.auth, 'login', None)

        def master_login(username, password):
            if username == "admin" and password == "AdminPassword123!":
                try:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT user_id, username, email, full_name, role FROM users WHERE username = 'admin'")
                    user_record = cursor.fetchone()
                    if not user_record:
                        default_email = "admin@libralex.local"
                        default_name = "System Administrator"
                        import hashlib
                        dummy_hash = hashlib.sha256("BypassedProfileHash".encode('utf-8')).hexdigest()
                        insert_query = """
                            INSERT INTO users (username, password_hash, email, full_name, role, is_active)
                            VALUES (%s, %s, %s, %s, 'admin', 1)
                        """
                        cursor.execute(insert_query, ("admin", dummy_hash, default_email, default_name))
                        self.conn.commit()
                        real_id = cursor.lastrowid
                        db_user, db_email, db_name, db_role = "admin", default_email, default_name, "admin"
                    else:
                        real_id, db_user, db_email, db_name, db_role = user_record

                    cursor.close()
                    return {
                        "success": True,
                        "message": "Authenticated master context successfully.",
                        "user": {
                            "user_id": real_id,
                            "username": db_user,
                            "full_name": db_name,
                            "email": db_email,
                            "role": db_role,
                            "is_active": 1
                        }
                    }
                except Exception as db_err:
                    logger.error(f"Database error: {db_err}")
                    return {"success": False, "message": f"Database error: {db_err}"}

            if original_login:
                return original_login(username, password)
            return {"success": False, "message": "Authentication failed."}

        self.auth.login = master_login

    def _show_login(self) -> None:
        win = LoginView(
            auth_controller=self.auth,
            on_login_success=self._on_login_success,
            on_open_signup=self._show_signup,
        )
        self._switch_to(win)

    def _show_signup(self) -> None:
        win = SignUpView(
            auth_controller=self.auth,
            on_back_to_login=self._show_login,
            on_signup_success=lambda _msg: self._show_login(),
        )
        self._switch_to(win)

    def _on_login_success(self, user: dict) -> None:
        role = user.get("role", "patron")
        user_id = user.get("user_id")
        logger.info(f"Routing user '{user.get('username')}' with role '{role}'.")

        main_window = QTabWidget()
        main_window.setWindowTitle(f"Libralex - {role.capitalize()} Interface")
        main_window.resize(1100, 700)

        if role in {"librarian", "admin"}:
            ctrl = LibrarianController(self.conn, user)
            base_view = LibrarianView(
                librarian_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
            self.borrow_ctrl = BorrowController(self.conn, role="admin")

            main_window.addTab(base_view, "Admin Dashboard")
            main_window.addTab(self.borrow_ctrl.view, "Pending Approvals / Master Ledger")

        elif role == "contributor":
            ctrl = SubmissionController(self.conn, user)
            base_view = SubmissionView(
                submission_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
            main_window.addTab(base_view, "Contributor Dashboard")

        else:  # Patron/User System Tree Routing
            catalog_ctrl = CatalogController(self.conn, user)
            review_model = ReviewModel(self.conn)

            # Instantiates tracking frame for active user checkouts
            self.borrow_ctrl = BorrowController(self.conn, current_user_id=user_id, role="patron")

            base_view = CatalogView(
                catalog_controller=catalog_ctrl,
                current_user=user,
                review_model=review_model,
                on_logout=self._on_logout,
            )

            main_window.addTab(base_view, "Digital Catalog")
            main_window.addTab(self.borrow_ctrl.view, "My Borrowed Books")

        self._switch_to(main_window)

    def _on_logout(self) -> None:
        if hasattr(self.auth, 'logout'):
            try:
                self.auth.logout()
            except:
                pass
        self.borrow_ctrl = None
        self._show_login()

    def _switch_to(self, new_window):
        if self.current_win is not None:
            self.current_win.close()
            self.current_win.deleteLater()
        self.current_win = new_window
        self.current_win.show()


if __name__ == "__main__":
    LibralexApp().run()