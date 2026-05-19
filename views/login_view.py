"""
Libralex Information System
views/login_view.py

Login screen for the Libralex application.
Features:
  - Libralex logo / branding header
  - Username + Password fields
  - Error message label
  - Enter key submits the form
  - Clear / Reset button
  - Link to open the Sign-Up view
  - Role-based dashboard routing on successful login
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QSizePolicy,
    QSpacerItem
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QKeyEvent
from PyQt6.QtCore import Qt, QSize


class LoginView(QWidget):
    """
    Login window for Libralex.

    Requires an AuthController instance to authenticate users and
    a callback/factory to open the correct dashboard after login.

    Usage:
        auth   = AuthController(conn)
        window = LoginView(auth_controller=auth, on_login_success=open_dashboard)
        window.show()

    Args:
        auth_controller:  An AuthController instance.
        on_login_success: Callable(current_user: dict) — called after
                          successful login so main.py can route to the
                          correct role-based dashboard.
        on_open_signup:   Callable() — called when the user clicks
                          "Create an account".
        parent:           Optional parent widget.
    """

    def __init__(
        self,
        auth_controller,
        on_login_success,
        on_open_signup,
        parent=None,
    ):
        super().__init__(parent)
        self.auth             = auth_controller
        self.on_login_success = on_login_success
        self.on_open_signup   = on_open_signup

        self._init_window()
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Libralex — Login")
        self.setMinimumSize(420, 540)
        self.setMaximumSize(480, 600)
        self.setObjectName("LoginView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#LoginView {
                background-color: #F7F4EF;
            }

            /* Card panel */
            QFrame#card {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0D9CF;
            }

            /* App title */
            QLabel#appTitle {
                font-size: 26px;
                font-weight: 700;
                color: #1B2A4A;
                letter-spacing: 1px;
            }

            QLabel#appSubtitle {
                font-size: 12px;
                color: #7A8499;
                letter-spacing: 2px;
            }

            /* Section heading */
            QLabel#sectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: #1B2A4A;
            }

            /* Field labels */
            QLabel.fieldLabel {
                font-size: 12px;
                font-weight: 600;
                color: #4A5568;
            }

            /* Input fields */
            QLineEdit {
                background-color: #F7F4EF;
                border: 1.5px solid #D1C9BC;
                border-radius: 7px;
                padding: 8px 12px;
                font-size: 13px;
                color: #1B2A4A;
                selection-background-color: #C5D5F5;
            }
            QLineEdit:focus {
                border-color: #3A6BBF;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #8AAAE0;
            }

            /* Primary button */
            QPushButton#btnLogin {
                background-color: #1B2A4A;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 10px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton#btnLogin:hover {
                background-color: #2A3F6F;
            }
            QPushButton#btnLogin:pressed {
                background-color: #111D33;
            }

            /* Secondary / ghost button */
            QPushButton#btnClear {
                background-color: transparent;
                color: #7A8499;
                border: 1.5px solid #D1C9BC;
                border-radius: 7px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton#btnClear:hover {
                background-color: #EDE8E0;
                color: #1B2A4A;
            }

            /* Sign-up link button */
            QPushButton#btnSignUp {
                background-color: transparent;
                color: #3A6BBF;
                border: none;
                font-size: 12px;
                text-decoration: underline;
                padding: 0;
            }
            QPushButton#btnSignUp:hover {
                color: #1B2A4A;
            }

            /* Error label */
            QLabel#errorLabel {
                color: #C0392B;
                font-size: 12px;
                background-color: #FDECEA;
                border: 1px solid #F5C6C2;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(0)

        # ---- Branding header ----
        root.addLayout(self._build_header())
        root.addSpacing(24)

        # ---- Card ----
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        # Section title
        section = QLabel("Sign In")
        section.setObjectName("sectionTitle")
        card_layout.addWidget(section)
        card_layout.addSpacing(4)

        # Username
        card_layout.addWidget(self._field_label("Username"))
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Enter your username")
        card_layout.addWidget(self.input_username)

        # Password
        card_layout.addWidget(self._field_label("Password"))
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Enter your password")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.input_password)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        card_layout.addSpacing(6)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setFixedHeight(38)

        self.btn_login = QPushButton("Sign In")
        self.btn_login.setObjectName("btnLogin")
        self.btn_login.setFixedHeight(38)
        self.btn_login.setDefault(True)

        btn_row.addWidget(self.btn_clear, 1)
        btn_row.addWidget(self.btn_login, 2)
        card_layout.addLayout(btn_row)

        card_layout.addSpacing(10)

        # Sign-up link
        signup_row = QHBoxLayout()
        signup_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signup_row.addWidget(QLabel("Don't have an account?"))
        self.btn_signup = QPushButton("Create an account")
        self.btn_signup.setObjectName("btnSignUp")
        self.btn_signup.setCursor(Qt.CursorShape.PointingHandCursor)
        signup_row.addWidget(self.btn_signup)
        card_layout.addLayout(signup_row)

        root.addWidget(card)
        root.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum,
                                       QSizePolicy.Policy.Expanding))

    def _build_header(self) -> QVBoxLayout:
        """Builds the Libralex branding block above the card."""
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo placeholder — replace src with actual logo path when available
        # logo = QLabel()
        # logo.setPixmap(QPixmap("assets/libralex_logo.png").scaled(
        #     64, 64, Qt.AspectRatioMode.KeepAspectRatio,
        #     Qt.TransformationMode.SmoothTransformation))
        # logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # layout.addWidget(logo)

        title = QLabel("LIBRALEX")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("INFO SYSTEM")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        return layout

    def _field_label(self, text: str) -> QLabel:
        """Returns a styled field label."""
        lbl = QLabel(text)
        lbl.setProperty("class", "fieldLabel")
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #4A5568;")
        return lbl

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_login.clicked.connect(self._handle_login)
        self.btn_clear.clicked.connect(self._handle_clear)
        self.btn_signup.clicked.connect(self._handle_open_signup)

        # Enter key on either field triggers login
        self.input_username.returnPressed.connect(self._handle_login)
        self.input_password.returnPressed.connect(self._handle_login)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_login(self):
        """Reads inputs, calls AuthController.login(), routes on success."""
        username = self.input_username.text().strip()
        password = self.input_password.text()

        # Client-side empty field check
        if not username:
            self._show_error("Please enter your username.")
            self.input_username.setFocus()
            return
        if not password:
            self._show_error("Please enter your password.")
            self.input_password.setFocus()
            return

        self._hide_error()
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in…")

        result = self.auth.login(username, password)

        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign In")

        if result["success"]:
            self._handle_clear()
            self.on_login_success(result["user"])   # Route to role-based dashboard
        else:
            self._show_error(result["message"])
            self.input_password.clear()
            self.input_password.setFocus()

    def _handle_clear(self):
        """Clears all inputs and hides any error message."""
        self.input_username.clear()
        self.input_password.clear()
        self._hide_error()
        self.input_username.setFocus()

    def _handle_open_signup(self):
        """Opens the Sign-Up view via the injected callback."""
        self.on_open_signup()

    # ------------------------------------------------------------------
    # Error display helpers
    # ------------------------------------------------------------------

    def _show_error(self, message: str):
        self.error_label.setText(f"⚠  {message}")
        self.error_label.show()

    def _hide_error(self):
        self.error_label.hide()
        self.error_label.setText("")
