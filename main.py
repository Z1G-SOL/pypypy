"""
Libralex Information System
main.py — Application entry point with Database-Linked Master Admin Hook

Run from the project root:
    python main.py
"""

import logging
import sys

# ---> ADDED QTabWidget to merge the windows together <---
from PyQt6.QtWidgets import QApplication, QMessageBox, QTabWidget

from database.db_connection import get_connection, test_connection
from controllers.auth_controller import AuthController
from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from controllers.librarian_controller import LibrarianController
# ---> IMPORTED BORROW ENGINE <---
from controllers.borrow_controller import BorrowController
from models.review_model import ReviewModel

from views.login_view import LoginView
from views.signup_view import SignUpView
from views.catalog_view import CatalogView
from views.submission_view import SubmissionView
from views.librarian_view import LibrarianView

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
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
        self.borrow_ctrl: BorrowController | None = None  # Holds the transaction state

    def run(self) -> None:
        """Entry point: boot DB, configure auth, and launch."""
        status = test_connection()
        if not status["success"]:
            QMessageBox.critical(
                None,
                "Database Error",
                f"Could not connect to the Libralex database.\n\n{status['message']}"
            )
            sys.exit(1)

        self.conn = get_connection()
        self.auth = AuthController(self.conn)

        # Inject the smart admin interceptor hook
        self._inject_admin_override()

        logger.info("Libralex started successfully.")
        self._show_login()
        sys.exit(self.app.exec())

    def _inject_admin_override(self) -> None:
        """
        Intercepts login logic. If credentials match, it ensures a valid row
        exists inside the database users table so foreign keys do not fail.
        """
        original_login = getattr(self.auth, 'login', None)

        def master_login(username, password):
            if username == "admin" and password == "AdminPassword123!":
                logger.info("Admin login detected. Verifying record table row constraints...")

                try:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT user_id, username, email, full_name, role FROM users WHERE username = 'admin'")
                    user_record = cursor.fetchone()

                    if user_record:
                        real_id, db_user, db_email, db_name, db_role = user_record
                    else:
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
                    logger.error(f"Database error while syncing admin row profile: {db_err}")
                    return {"success": False, "message": f"Database error syncing admin profile: {db_err}"}

            if original_login:
                return original_login(username, password)
            return {"success": False, "message": "Authentication core pipeline processing failed."}

        self.auth.login = master_login

    # ------------------------------------------------------------------
    # Window routing & event routines
    # ------------------------------------------------------------------

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
        logger.info("Routing user '%s' with role '%s' post-login.", user.get("username"), role)

        # ------------------------------------------------------------------
        # NEW INTEGRATION: We create a single Master Window holding everything
        # ------------------------------------------------------------------
        main_window = QTabWidget()
        main_window.setWindowTitle(f"Libralex - {role.capitalize()} Interface")
        main_window.resize(1100, 700)  # Sets a clean size for the integrated app

        if role in {"librarian", "admin"}:
            ctrl = LibrarianController(self.conn, user)
            base_view = LibrarianView(
                librarian_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
            # Initialize the admin borrowing ledger
            self.borrow_ctrl = BorrowController(self.conn, role="admin")

            # Embed both into the main window tabs!
            main_window.addTab(base_view, "Admin Dashboard")
            main_window.addTab(self.borrow_ctrl.view, "Pending Approvals / Master Ledger")

        elif role == "contributor":
            ctrl = SubmissionController(self.conn, user)
            base_view = SubmissionView(
                submission_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
            # Contributors just get their submission view
            main_window.addTab(base_view, "Contributor Dashboard")

        else: # Standard Patron / User
            ctrl         = CatalogController(self.conn, user)
            review_model = ReviewModel(self.conn)
            base_view    = CatalogView(
                catalog_controller=ctrl,
                current_user=user,
                review_model=review_model,
                on_logout=self._on_logout,
            )
            # Initialize the user's personal borrowing history
            self.borrow_ctrl = BorrowController(self.conn, current_user_id=user_id, role="user")

            # Embed both into the main window tabs!
            main_window.addTab(base_view, "Digital Catalog")
            main_window.addTab(self.borrow_ctrl.view, "My Borrowed Books")

        # Route the app to show the unified window instead of separate pop-ups
        self._switch_to(main_window)

    def _on_logout(self) -> None:
        if hasattr(self.auth, 'logout') and callable(self.auth.logout):
            try: self.auth.logout()
            except: pass

        # Clean up the memory references safely
        self.borrow_ctrl = None
        self._show_login()

    def _switch_to(self, new_window) -> None:
        if self.current_win is not None:
            self.current_win.close()
            self.current_win.deleteLater()
        self.current_win = new_window
        self.current_win.show()


if __name__ == "__main__":
    LibralexApp().run()