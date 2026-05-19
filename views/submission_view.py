"""
Libralex Information System
views/submission_view.py

Alexandria Archives — Digital Submission Portal.
Allows contributors to submit digital works (PDF/DOCX) for librarian review.
Also shows the contributor's submission history with current status.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QTableWidget, QTableWidgetItem,
    QFileDialog, QHeaderView, QAbstractItemView, QSplitter,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
import os


class SubmissionView(QWidget):
    """
    Alexandria Archives submission portal.

    Usage:
        ctrl = SubmissionController(conn, current_user)
        view = SubmissionView(submission_controller=ctrl,
                              current_user=auth.current_user,
                              on_logout=logout_fn)
        view.show()
    """

    def __init__(self, submission_controller, current_user, on_logout, parent=None):
        super().__init__(parent)
        self.ctrl       = submission_controller
        self.user       = current_user
        self.on_logout  = on_logout
        self._submissions = []

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._load_my_submissions()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Libralex — Alexandria Archives")
        self.setMinimumSize(860, 580)
        self.setObjectName("SubmissionView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#SubmissionView { background-color: #F7F4EF; }
            QLabel#pageTitle  { font-size: 20px; font-weight: 700; color: #1B2A4A; }
            QLabel#userBadge  { font-size: 11px; color: #7A8499; }
            QLabel#sectionTitle { font-size: 14px; font-weight: 600; color: #1B2A4A; }
            QLabel#fieldLabel { font-size: 12px; font-weight: 600; color: #4A5568; }
            QFrame#formCard, QFrame#historyCard {
                background-color: #FFFFFF; border: 1px solid #E0D9CF; border-radius: 10px;
            }
            QLineEdit, QTextEdit {
                background-color: #F7F4EF; border: 1.5px solid #D1C9BC;
                border-radius: 6px; padding: 7px 10px; font-size: 12px; color: #1B2A4A;
            }
            QLineEdit:focus, QTextEdit:focus { border-color: #3A6BBF; background-color: #FFFFFF; }
            QPushButton#btnSubmit {
                background-color: #1B2A4A; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 9px; font-size: 13px; font-weight: 600;
            }
            QPushButton#btnSubmit:hover { background-color: #2A3F6F; }
            QPushButton#btnClear {
                background-color: transparent; color: #7A8499;
                border: 1.5px solid #D1C9BC; border-radius: 6px; padding: 9px; font-size: 12px;
            }
            QPushButton#btnClear:hover { background-color: #EDE8E0; }
            QPushButton#btnBrowse {
                background-color: #EAF0FB; color: #1B2A4A; border: 1px solid #BDD0F8;
                border-radius: 6px; padding: 7px 12px; font-size: 12px;
            }
            QPushButton#btnBrowse:hover { background-color: #D6E4F7; }
            QPushButton#btnRefresh {
                background-color: transparent; color: #3A6BBF;
                border: 1px solid #BDD0F8; border-radius: 6px; padding: 5px 12px; font-size: 11px;
            }
            QPushButton#btnLogout {
                background-color: transparent; color: #C0392B;
                border: 1.5px solid #F5C6C2; border-radius: 6px; padding: 6px 14px; font-size: 12px;
            }
            QPushButton#btnLogout:hover { background-color: #FDECEA; }
            QTableWidget {
                background-color: #FFFFFF; border: none;
                gridline-color: #F0EBE3; selection-background-color: #EAF0FB;
            }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; font-size: 12px; }
            QHeaderView::section {
                background-color: #F0EBE3; color: #4A5568; font-weight: 600; font-size: 11px;
                padding: 6px 10px; border: none; border-bottom: 1px solid #D1C9BC;
            }
            QLabel#errorLabel {
                color: #C0392B; font-size: 11px; background-color: #FDECEA;
                border: 1px solid #F5C6C2; border-radius: 5px; padding: 5px 8px;
            }
            QLabel#successLabel {
                color: #1E7E34; font-size: 11px; background-color: #E9F7EC;
                border: 1px solid #A8D5B0; border-radius: 5px; padding: 5px 8px;
            }
        """)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addLayout(self._build_topbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._build_form_card())
        splitter.addWidget(self._build_history_card())
        splitter.setSizes([440, 420])

        root.addWidget(splitter, stretch=1)

    def _build_topbar(self):
        row = QHBoxLayout()
        title = QLabel("📜  Alexandria Archives")
        title.setObjectName("pageTitle")
        row.addWidget(title)
        row.addStretch()
        badge = QLabel(
            f"Logged in as  {self.user.get('username','')}  "
            f"[{self.user.get('role','').upper()}]"
        )
        badge.setObjectName("userBadge")
        row.addWidget(badge)
        row.addSpacing(10)
        btn_logout = QPushButton("Logout")
        btn_logout.setObjectName("btnLogout")
        btn_logout.clicked.connect(self.on_logout)
        row.addWidget(btn_logout)
        return row

    def _build_form_card(self):
        card = QFrame()
        card.setObjectName("formCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        sec = QLabel("Submit a Digital Work")
        sec.setObjectName("sectionTitle")
        layout.addWidget(sec)
        layout.addSpacing(4)

        # Title
        layout.addWidget(self._lbl("Title *"))
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("Title of your work")
        layout.addWidget(self.input_title)

        # Author
        layout.addWidget(self._lbl("Author(s) *"))
        self.input_author = QLineEdit()
        self.input_author.setPlaceholderText("Author name(s)")
        layout.addWidget(self.input_author)

        # Abstract
        layout.addWidget(self._lbl("Abstract *"))
        self.input_abstract = QTextEdit()
        self.input_abstract.setPlaceholderText("Brief description of the work…")
        self.input_abstract.setFixedHeight(90)
        layout.addWidget(self.input_abstract)

        # File upload row
        layout.addWidget(self._lbl("Upload File * (PDF or DOCX)"))
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.input_filepath = QLineEdit()
        self.input_filepath.setPlaceholderText("No file selected")
        self.input_filepath.setReadOnly(True)
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setObjectName("btnBrowse")
        self.btn_browse.setFixedHeight(32)
        file_row.addWidget(self.input_filepath)
        file_row.addWidget(self.btn_browse)
        layout.addLayout(file_row)

        # Feedback
        self.form_error = QLabel("")
        self.form_error.setObjectName("errorLabel")
        self.form_error.setWordWrap(True)
        self.form_error.hide()
        layout.addWidget(self.form_error)

        self.form_success = QLabel("")
        self.form_success.setObjectName("successLabel")
        self.form_success.setWordWrap(True)
        self.form_success.hide()
        layout.addWidget(self.form_success)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("btnClear")
        self.btn_clear.setFixedHeight(38)
        self.btn_submit = QPushButton("Submit Work")
        self.btn_submit.setObjectName("btnSubmit")
        self.btn_submit.setFixedHeight(38)
        btn_row.addWidget(self.btn_clear, 1)
        btn_row.addWidget(self.btn_submit, 2)
        layout.addLayout(btn_row)

        return card

    def _build_history_card(self):
        card = QFrame()
        card.setObjectName("historyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        head_row = QHBoxLayout()
        sec = QLabel("My Submissions")
        sec.setObjectName("sectionTitle")
        head_row.addWidget(sec)
        head_row.addStretch()
        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setObjectName("btnRefresh")
        self.btn_refresh.setFixedHeight(28)
        head_row.addWidget(self.btn_refresh)
        layout.addLayout(head_row)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Title", "Author", "Status", "Submitted"])
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table, stretch=1)

        self.history_status = QLabel("")
        self.history_status.setStyleSheet("font-size: 11px; color: #7A8499;")
        layout.addWidget(self.history_status)

        return card

    def _lbl(self, text):
        l = QLabel(text)
        l.setObjectName("fieldLabel")
        l.setStyleSheet("font-size: 12px; font-weight: 600; color: #4A5568;")
        return l

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_submit.clicked.connect(self._handle_submit)
        self.btn_clear.clicked.connect(self._handle_clear)
        self.btn_browse.clicked.connect(self._handle_browse)
        self.btn_refresh.clicked.connect(self._load_my_submissions)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "",
            "Supported Files (*.pdf *.docx);;PDF Files (*.pdf);;Word Documents (*.docx)"
        )
        if path:
            self.input_filepath.setText(path)

    def _handle_submit(self):
        self._hide_feedback()
        title    = self.input_title.text().strip()
        author   = self.input_author.text().strip()
        abstract = self.input_abstract.toPlainText().strip()
        filepath = self.input_filepath.text().strip()

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("Submitting…")

        result = self.ctrl.submit_work(
            title=title, author=author, abstract=abstract, file_path=filepath
        )

        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("Submit Work")

        if result["success"]:
            self._show_success("Submission received! Pending librarian review.")
            self._handle_clear()
            self._load_my_submissions()
        else:
            self._show_error(result["message"])

    def _handle_clear(self):
        self.input_title.clear()
        self.input_author.clear()
        self.input_abstract.clear()
        self.input_filepath.clear()
        self._hide_feedback()

    def _load_my_submissions(self):
        result = self.ctrl.get_my_submissions()
        self._submissions = result.get("submissions", [])
        self._populate_history(self._submissions)
        self.history_status.setText(result.get("message", ""))

    def _populate_history(self, submissions):
        STATUS_COLORS = {
            "pending":  "#B7791F",
            "approved": "#1E7E34",
            "rejected": "#C0392B",
        }
        self.history_table.setRowCount(0)
        for sub in submissions:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(sub.get("title", "")))
            self.history_table.setItem(row, 1, QTableWidgetItem(sub.get("author", "")))

            status = sub.get("status", "pending")
            status_item = QTableWidgetItem(status.capitalize())
            color = STATUS_COLORS.get(status, "#4A5568")
            status_item.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(color)
            )
            self.history_table.setItem(row, 2, status_item)

            date_val = sub.get("date_submitted", "")
            date_str = str(date_val)[:10] if date_val else "—"
            self.history_table.setItem(row, 3, QTableWidgetItem(date_str))

        self.history_table.resizeRowsToContents()

    # ------------------------------------------------------------------
    # Feedback helpers
    # ------------------------------------------------------------------

    def _show_error(self, msg):
        self.form_error.setText(f"⚠  {msg}")
        self.form_error.show()

    def _show_success(self, msg):
        self.form_success.setText(f"✓  {msg}")
        self.form_success.show()

    def _hide_feedback(self):
        self.form_error.hide()
        self.form_success.hide()
