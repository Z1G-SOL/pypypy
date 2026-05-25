"""
Libralex Information System
views/signup_view.py

Sign-Up / Registration screen.
Allows new patrons and contributors to self-register.
Librarian/admin accounts require an admin session (enforced by AuthController).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QComboBox,
    QSizePolicy, QSpacerItem, QScrollArea
)
from PyQt6.QtCore import Qt


class SignUpView(QWidget):
    """
    Registration window for Libralex.

    Usage:
        auth   = AuthController(conn)
        window = SignUpView(auth_controller=auth, on_back_to_login=show_login)
        window.show()

    Args:
        auth_controller:  An AuthController instance.
        on_back_to_login: Callable() — returns to the Login view.
        on_signup_success: Callable(message: str) — called on success so
                           caller can show a confirmation and redirect.
        parent:           Optional parent widget.
    """

    def __init__(self, auth_controller, on_back_to_login, on_signup_success, parent=None):
        super().__init__(parent)
        self.auth              = auth_controller
        self.on_back_to_login  = on_back_to_login
        self.on_signup_success = on_signup_success

        self._init_window()
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Libralex — Create Account")
        self.setMinimumSize(440, 640)
        self.setMaximumSize(500, 720)
        self.setObjectName("SignUpView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#SignUpView { background-color: #F7F4EF; }
            QFrame#card {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0D9CF;
            }
            QLabel#appTitle  { font-size: 24px; font-weight: 700; color: #1B2A4A; letter-spacing: 1px; }
            QLabel#appSubtitle { font-size: 11px; color: #7A8499; letter-spacing: 2px; }
            QLabel#sectionTitle { font-size: 16px; font-weight: 600; color: #1B2A4A; }
            QLineEdit, QComboBox {
                background-color: #F7F4EF;
                border: 1.5px solid #D1C9BC;
                border-radius: 7px;
                padding: 8px 12px;
                font-size: 13px;
                color: #1B2A4A;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3A6BBF; background-color: #FFFFFF; }
            QLineEdit:hover, QComboBox:hover { border-color: #8AAAE0; }
            QPushButton#btnSubmit {
                background-color: #1B2A4A; color: #FFFFFF;
                border: none; border-radius: 7px;
                padding: 10px; font-size: 13px; font-weight: 600;
            }
            QPushButton#btnSubmit:hover { background-color: #2A3F6F; }
            QPushButton#btnSubmit:pressed { background-color: #111D33; }
            QPushButton#btnBack {
                background-color: transparent; color: #7A8499;
                border: 1.5px solid #D1C9BC; border-radius: 7px;
                padding: 10px; font-size: 13px;
            }
            QPushButton#btnBack:hover { background-color: #EDE8E0; color: #1B2A4A; }
            QLabel#errorLabel {
                color: #C0392B; font-size: 12px;
                background-color: #FDECEA; border: 1px solid #F5C6C2;
                border-radius: 6px; padding: 6px 10px;
            }
            QLabel#successLabel {
                color: #1E7E34; font-size: 12px;
                background-color: #E9F7EC; border: 1px solid #A8D5B0;
                border-radius: 6px; padding: 6px 10px;
            }
        """)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(0)

        # Branding
        root.addLayout(self._build_header())
        root.addSpacing(20)

        # Scrollable card
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        section = QLabel("Create Account")
        section.setObjectName("sectionTitle")
        card_layout.addWidget(section)
        card_layout.addSpacing(4)

        # Full name
        card_layout.addWidget(self._field_label("Full Name *"))
        self.input_full_name = QLineEdit()
        self.input_full_name.setPlaceholderText("e.g. Juan dela Cruz")
        card_layout.addWidget(self.input_full_name)

        # Username
        card_layout.addWidget(self._field_label("Username *"))
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Choose a unique username")
        card_layout.addWidget(self.input_username)

        # Email
        card_layout.addWidget(self._field_label("Email Address *"))
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("your@email.com")
        card_layout.addWidget(self.input_email)

        # Contact number
        card_layout.addWidget(self._field_label("Contact Number (optional)"))
        self.input_contact = QLineEdit()
        self.input_contact.setPlaceholderText("+63 9XX XXX XXXX")
        card_layout.addWidget(self.input_contact)

        # Role
        card_layout.addWidget(self._field_label("Role *"))
        self.input_role = QComboBox()
        self.input_role.addItems(["patron", "contributor"])
        card_layout.addWidget(self.input_role)

        # Password
        card_layout.addWidget(self._field_label("Password *"))
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Minimum 8 characters")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.input_password)

        # Confirm password
        card_layout.addWidget(self._field_label("Confirm Password *"))
        self.input_confirm = QLineEdit()
        self.input_confirm.setPlaceholderText("Re-enter your password")
        self.input_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.input_confirm)

        # Feedback labels
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        self.success_label = QLabel("")
        self.success_label.setObjectName("successLabel")
        self.success_label.setWordWrap(True)
        self.success_label.hide()
        card_layout.addWidget(self.success_label)

        card_layout.addSpacing(4)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_back = QPushButton("← Back")
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setFixedHeight(38)
        self.btn_submit = QPushButton("Create Account")
        self.btn_submit.setObjectName("btnSubmit")
        self.btn_submit.setFixedHeight(38)
        btn_row.addWidget(self.btn_back, 1)
        btn_row.addWidget(self.btn_submit, 2)
        card_layout.addLayout(btn_row)

        scroll.setWidget(card)
        root.addWidget(scroll)

    def _build_header(self):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("LIBRALEX")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("INFO SYSTEM")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        return layout

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #4A5568;")
        return lbl

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_submit.clicked.connect(self._handle_submit)
        self.btn_back.clicked.connect(self.on_back_to_login)
        self.input_confirm.returnPressed.connect(self._handle_submit)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_submit(self):
        self._hide_feedback()

        full_name      = self.input_full_name.text().strip()
        username       = self.input_username.text().strip()
        email          = self.input_email.text().strip()
        contact        = self.input_contact.text().strip() or None
        role           = self.input_role.currentText()
        password       = self.input_password.text()
        confirm        = self.input_confirm.text()

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("Creating account…")

        result = self.auth.register(
            username=username,
            password=password,
            confirm_password=confirm,
            email=email,
            full_name=full_name,
            role=role,
            contact_number=contact,
        )

        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("Create Account")

        if result["success"]:
            self._show_success("Account created! You can now log in.")
            self._clear_fields()
            self.on_signup_success(result["message"])
        else:
            self._show_error(result["message"])

    def _clear_fields(self):
        for field in [self.input_full_name, self.input_username,
                      self.input_email, self.input_contact,
                      self.input_password, self.input_confirm]:
            field.clear()
        self.input_role.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Feedback helpers
    # ------------------------------------------------------------------

    def _show_error(self, msg):
        self.error_label.setText(f"⚠  {msg}")
        self.error_label.show()

    def _show_success(self, msg):
        self.success_label.setText(f"✓  {msg}")
        self.success_label.show()

    def _hide_feedback(self):
        self.error_label.hide()
        self.success_label.hide()