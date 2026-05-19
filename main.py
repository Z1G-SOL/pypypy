"""
Libralex Information System
main.py — Application entry point

Run from the project root:
    python main.py

Requires a .env file (or exported environment variables) for DB credentials.
See database/db_connection.py and the project README for setup instructions.
"""

import logging
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from database.db_connection import get_connection, test_connection
from controllers.auth_controller import AuthController
from controllers.catalog_controller import CatalogController
from controllers.submission_controller import SubmissionController
from controllers.librarian_controller import LibrarianController
from models.review_model import ReviewModel

from views.login_view import LoginView
from views.signup_view import SignUpView
from views.catalog_view import CatalogView
from views.submission_view import SubmissionView
from views.librarian_view import LibrarianView

# ---------------------------------------------------------------------------
# Logging — emit INFO+ to stdout; adjust level or add file handler as needed.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class LibralexApp:
    """
    Application shell responsible for bootstrapping the DB connection,
    constructing the initial view, and routing between windows.

    The class keeps exactly one window alive at a time; switching calls
    ``close()`` and ``deleteLater()`` on the outgoing window before
    displaying the incoming one.
    """

    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Libralex")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Libralex Info System")

        self.conn: object | None = None
        self.auth: AuthController | None = None
        self.current_win: object | None = None

    def run(self) -> None:
        """
        Entry point: probe the DB, then launch the login screen.
        Exits the process on DB failure.
        """
        status = test_connection()
        if not status["success"]:
            QMessageBox.critical(
                None,
                "Database Error",
                f"Could not connect to the Libralex database.\n\n"
                f"{status['message']}\n\n"
                "Please check your .env file (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME) "
                "and try again.",
            )
            logger.critical("DB connection failed at startup: %s", status["message"])
            sys.exit(1)

        self.conn = get_connection()
        self.auth = AuthController(self.conn)
        logger.info("Libralex started successfully.")
        self._show_login()
        sys.exit(self.app.exec())

    # ------------------------------------------------------------------
    # Window routing
    # ------------------------------------------------------------------

    def _show_login(self) -> None:
        """Display the login screen."""
        win = LoginView(
            auth_controller=self.auth,
            on_login_success=self._on_login_success,
            on_open_signup=self._show_signup,
        )
        self._switch_to(win)

    def _show_signup(self) -> None:
        """Display the sign-up / registration screen."""
        win = SignUpView(
            auth_controller=self.auth,
            on_back_to_login=self._show_login,
            on_signup_success=lambda _msg: self._show_login(),
        )
        self._switch_to(win)

    def _on_login_success(self, user: dict) -> None:
        """
        Route the authenticated user to the appropriate view based on role.

        Args:
            user (dict): Authenticated user dict (password_hash already stripped).
        """
        role = user.get("role", "patron")
        logger.info("Routing user '%s' with role '%s' post-login.", user.get("username"), role)

        if role in {"librarian", "admin"}:
            ctrl = LibrarianController(self.conn, user)
            win  = LibrarianView(
                librarian_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
        elif role == "contributor":
            ctrl = SubmissionController(self.conn, user)
            win  = SubmissionView(
                submission_controller=ctrl,
                current_user=user,
                on_logout=self._on_logout,
            )
        else:  # patron (default)
            ctrl         = CatalogController(self.conn, user)
            review_model = ReviewModel(self.conn)
            win          = CatalogView(
                catalog_controller=ctrl,
                current_user=user,
                review_model=review_model,
                on_logout=self._on_logout,
            )

        self._switch_to(win)

    def _on_logout(self) -> None:
        """Terminate the session and return to the login screen."""
        self.auth.logout()
        self._show_login()

    def _switch_to(self, new_window) -> None:
        """
        Replace the current window with *new_window*.

        The outgoing window is closed and scheduled for Qt object deletion
        via ``deleteLater()`` to prevent memory leaks under PyQt6's
        object lifecycle model.

        Args:
            new_window: The incoming QWidget subclass to display.
        """
        if self.current_win is not None:
            self.current_win.close()
            self.current_win.deleteLater()
        self.current_win = new_window
        self.current_win.show()


if __name__ == "__main__":
    LibralexApp().run()