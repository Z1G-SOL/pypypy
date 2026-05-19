"""
Libralex Information System
main.py — Application entry point

Run this file from the Libralex/ root folder:
    python main.py
"""

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


class LibralexApp:
    def __init__(self):
        self.app  = QApplication(sys.argv)
        self.app.setApplicationName("Libralex")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Libralex Info System")
        self.conn        = None
        self.auth        = None
        self.current_win = None

    def run(self):
        status = test_connection()
        if not status["success"]:
            QMessageBox.critical(
                None, "Database Error",
                f"Could not connect to the Libralex database.\n\n"
                f"{status['message']}\n\n"
                "Please check database/db_connection.py and try again.")
            sys.exit(1)

        self.conn = get_connection()
        self.auth = AuthController(self.conn)
        self._show_login()
        sys.exit(self.app.exec())

    def _show_login(self):
        win = LoginView(
            auth_controller=self.auth,
            on_login_success=self._on_login_success,
            on_open_signup=self._show_signup)
        self._switch_to(win)

    def _show_signup(self):
        win = SignUpView(
            auth_controller=self.auth,
            on_back_to_login=self._show_login,
            on_signup_success=lambda msg: self._show_login())
        self._switch_to(win)

    def _on_login_success(self, user):
        role = user.get("role", "patron")
        if role in {"librarian", "admin"}:
            ctrl = LibrarianController(self.conn, user)
            win  = LibrarianView(librarian_controller=ctrl, current_user=user, on_logout=self._on_logout)
        elif role == "contributor":
            sub_ctrl = SubmissionController(self.conn, user)
            win = SubmissionView(submission_controller=sub_ctrl, current_user=user, on_logout=self._on_logout)
        else:
            cat_ctrl     = CatalogController(self.conn, user)
            review_model = ReviewModel(self.conn)
            win = CatalogView(catalog_controller=cat_ctrl, current_user=user,
                              review_model=review_model, on_logout=self._on_logout)
        self._switch_to(win)

    def _on_logout(self):
        self.auth.logout()
        self._show_login()

    def _switch_to(self, new_window):
        if self.current_win:
            self.current_win.close()
        self.current_win = new_window
        self.current_win.show()


if __name__ == "__main__":
    LibralexApp().run()
