"""
Libralex Information System
views/librarian_view.py

Librarian Dashboard — tabbed interface for librarian and admin roles.
Tabs:
  1. Dashboard   — summary counts panel
  2. Submissions — pending submission review queue
  3. Reviews     — pending patron review moderation queue
  4. Catalog     — full catalog management (add/edit/delete books)
  5. Users       — patron/contributor account management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QFrame,
    QHeaderView, QAbstractItemView, QTextEdit, QLineEdit,
    QComboBox, QMessageBox, QGridLayout, QSizePolicy, QDialog,
    QDialogButtonBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class LibrarianView(QWidget):
    """
    Librarian / Admin Dashboard.

    Usage:
        lib_ctrl = LibrarianController(conn, current_user)
        view = LibrarianView(librarian_controller=lib_ctrl,
                             current_user=auth.current_user,
                             on_logout=logout_fn)
        view.show()
    """

    def __init__(self, librarian_controller, current_user, on_logout, parent=None):
        super().__init__(parent)
        self.ctrl      = librarian_controller
        self.user      = current_user
        self.on_logout = on_logout

        self._init_window()
        self._build_ui()
        self._load_all()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Libralex — Librarian Dashboard")
        self.setMinimumSize(1000, 660)
        self.setObjectName("LibrarianView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#LibrarianView { background-color: #F7F4EF; }
            QLabel#pageTitle   { font-size: 20px; font-weight: 700; color: #1B2A4A; }
            QLabel#userBadge   { font-size: 11px; color: #7A8499; }
            QTabWidget::pane   { border: 1px solid #E0D9CF; border-radius: 8px; background: #FFFFFF; }
            QTabBar::tab {
                background: #EDE8E0; color: #4A5568; padding: 8px 20px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                margin-right: 3px; font-size: 12px;
            }
            QTabBar::tab:selected { background: #FFFFFF; color: #1B2A4A; font-weight: 600; }
            QTabBar::tab:hover    { background: #E0D9CF; }
            /* Stat cards */
            QFrame#statCard {
                background-color: #FFFFFF; border: 1px solid #E0D9CF;
                border-radius: 10px; padding: 8px;
            }
            QLabel#statValue { font-size: 28px; font-weight: 700; color: #1B2A4A; }
            QLabel#statLabel { font-size: 11px; color: #7A8499; }
            /* Tables */
            QTableWidget {
                background-color: #FFFFFF; border: none;
                gridline-color: #F0EBE3; selection-background-color: #EAF0FB;
                alternate-background-color: #FAF8F5;
            }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; font-size: 12px; }
            QHeaderView::section {
                background-color: #F0EBE3; color: #4A5568; font-weight: 600; font-size: 11px;
                padding: 7px 10px; border: none; border-bottom: 1px solid #D1C9BC;
            }
            /* Buttons */
            QPushButton#btnApprove {
                background-color: #E9F7EC; color: #1E7E34; border: 1px solid #A8D5B0;
                border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: 600;
            }
            QPushButton#btnReject {
                background-color: #FDECEA; color: #C0392B; border: 1px solid #F5C6C2;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnEdit {
                background-color: #E8F0FE; color: #1B2A4A; border: 1px solid #BDD0F8;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnDelete {
                background-color: #FDECEA; color: #C0392B; border: 1px solid #F5C6C2;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnDeactivate {
                background-color: #FFF8E1; color: #B7791F; border: 1px solid #F6E2A0;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnReactivate {
                background-color: #E9F7EC; color: #1E7E34; border: 1px solid #A8D5B0;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnPrimary {
                background-color: #1B2A4A; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 7px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton#btnPrimary:hover { background-color: #2A3F6F; }
            QPushButton#btnSecondary {
                background-color: transparent; color: #7A8499;
                border: 1.5px solid #D1C9BC; border-radius: 6px; padding: 7px 14px; font-size: 12px;
            }
            QPushButton#btnLogout {
                background-color: transparent; color: #C0392B;
                border: 1.5px solid #F5C6C2; border-radius: 6px; padding: 6px 14px; font-size: 12px;
            }
            QPushButton#btnLogout:hover { background-color: #FDECEA; }
            QLineEdit, QComboBox {
                background-color: #F7F4EF; border: 1.5px solid #D1C9BC;
                border-radius: 6px; padding: 6px 10px; font-size: 12px; color: #1B2A4A;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3A6BBF; }
        """)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(12)
        root.addLayout(self._build_topbar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_dashboard_tab(),   "🏠  Dashboard")
        self.tabs.addTab(self._build_submissions_tab(), "📥  Submissions")
        self.tabs.addTab(self._build_reviews_tab(),     "⭐  Reviews")
        self.tabs.addTab(self._build_catalog_tab(),     "📚  Catalog")
        self.tabs.addTab(self._build_users_tab(),       "👥  Users")
        root.addWidget(self.tabs, stretch=1)

    def _build_topbar(self):
        row = QHBoxLayout()
        title = QLabel("🛡  Librarian Dashboard")
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
        btn_refresh = QPushButton("↻ Refresh All")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self._load_all)
        row.addWidget(btn_refresh)
        row.addSpacing(8)
        btn_logout = QPushButton("Logout")
        btn_logout.setObjectName("btnLogout")
        btn_logout.clicked.connect(self.on_logout)
        row.addWidget(btn_logout)
        return row

    # ── Dashboard tab ─────────────────────────────────────────────────

    def _build_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        heading = QLabel("Overview")
        heading.setStyleSheet("font-size: 15px; font-weight: 600; color: #1B2A4A;")
        layout.addWidget(heading)

        self.stat_grid = QGridLayout()
        self.stat_grid.setSpacing(12)
        layout.addLayout(self.stat_grid)
        layout.addStretch()
        return widget

    def _populate_dashboard(self, summary):
        # Clear previous stat cards
        while self.stat_grid.count():
            item = self.stat_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = [
            ("Pending Submissions", summary.get("pending_submissions", 0),  "#B7791F"),
            ("Approved Submissions", summary.get("approved_submissions", 0), "#1E7E34"),
            ("Rejected Submissions", summary.get("rejected_submissions", 0), "#C0392B"),
            ("Pending Reviews",      summary.get("pending_reviews", 0),      "#3A6BBF"),
            ("Total Books",          summary.get("total_books", 0),          "#1B2A4A"),
            ("Total Users",          summary.get("total_users", 0),          "#1B2A4A"),
            ("Patrons",              summary.get("total_patrons", 0),        "#4A5568"),
            ("Contributors",         summary.get("total_contributors", 0),   "#4A5568"),
        ]

        for i, (label, value, color) in enumerate(stats):
            card = QFrame()
            card.setObjectName("statCard")
            card.setMinimumSize(160, 80)
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl = QLabel(str(value))
            val_lbl.setObjectName("statValue")
            val_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setObjectName("statLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(val_lbl)
            card_layout.addWidget(lbl)
            self.stat_grid.addWidget(card, i // 4, i % 4)

    # ── Submissions tab ───────────────────────────────────────────────

    def _build_submissions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Pending Submissions"))
        head_row.addStretch()
        btn_ref = QPushButton("↻ Refresh")
        btn_ref.setObjectName("btnSecondary")
        btn_ref.setFixedHeight(28)
        btn_ref.clicked.connect(self._load_submissions)
        head_row.addWidget(btn_ref)
        layout.addLayout(head_row)

        self.sub_table = QTableWidget(0, 6)
        self.sub_table.setHorizontalHeaderLabels(
            ["Title", "Author", "Contributor", "Submitted", "File", "Actions"]
        )
        self._setup_table(self.sub_table)
        self.sub_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sub_table, stretch=1)

        self.sub_status = QLabel("")
        self.sub_status.setStyleSheet("font-size: 11px; color: #7A8499;")
        layout.addWidget(self.sub_status)
        return widget

    # ── Reviews tab ───────────────────────────────────────────────────

    def _build_reviews_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Pending Reviews"))
        head_row.addStretch()
        btn_ref = QPushButton("↻ Refresh")
        btn_ref.setObjectName("btnSecondary")
        btn_ref.setFixedHeight(28)
        btn_ref.clicked.connect(self._load_reviews)
        head_row.addWidget(btn_ref)
        layout.addLayout(head_row)

        self.rev_table = QTableWidget(0, 5)
        self.rev_table.setHorizontalHeaderLabels(
            ["Book Title", "Reviewer", "Review Text", "Date", "Actions"]
        )
        self._setup_table(self.rev_table)
        self.rev_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rev_table, stretch=1)

        self.rev_status = QLabel("")
        self.rev_status.setStyleSheet("font-size: 11px; color: #7A8499;")
        layout.addWidget(self.rev_status)
        return widget

    # ── Catalog tab ───────────────────────────────────────────────────

    def _build_catalog_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("Catalog Management"))
        head_row.addStretch()
        btn_add = QPushButton("+ Add Book")
        btn_add.setObjectName("btnPrimary")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._on_add_book)
        head_row.addWidget(btn_add)
        btn_ref = QPushButton("↻ Refresh")
        btn_ref.setObjectName("btnSecondary")
        btn_ref.setFixedHeight(30)
        btn_ref.clicked.connect(self._load_catalog)
        head_row.addWidget(btn_ref)
        layout.addLayout(head_row)

        # Search bar
        search_row = QHBoxLayout()
        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("Search catalog…")
        self.catalog_search.setFixedHeight(32)
        self.catalog_search.returnPressed.connect(self._load_catalog)
        search_row.addWidget(self.catalog_search)
        btn_s = QPushButton("Search")
        btn_s.setObjectName("btnPrimary")
        btn_s.setFixedHeight(32)
        btn_s.clicked.connect(self._load_catalog)
        search_row.addWidget(btn_s)
        layout.addLayout(search_row)

        self.cat_table = QTableWidget(0, 6)
        self.cat_table.setHorizontalHeaderLabels(
            ["Title", "Author", "Year", "Format", "Tags", "Actions"]
        )
        self._setup_table(self.cat_table)
        self.cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.cat_table, stretch=1)

        self.cat_status = QLabel("")
        self.cat_status.setStyleSheet("font-size: 11px; color: #7A8499;")
        layout.addWidget(self.cat_status)
        return widget

    # ── Users tab ─────────────────────────────────────────────────────

    def _build_users_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head_row = QHBoxLayout()
        head_row.addWidget(QLabel("User Management"))
        head_row.addStretch()
        self.user_role_filter = QComboBox()
        self.user_role_filter.addItems(["All Roles", "patron", "contributor", "librarian", "admin"])
        self.user_role_filter.setFixedHeight(30)
        self.user_role_filter.currentTextChanged.connect(self._load_users)
        head_row.addWidget(self.user_role_filter)
        btn_ref = QPushButton("↻ Refresh")
        btn_ref.setObjectName("btnSecondary")
        btn_ref.setFixedHeight(30)
        btn_ref.clicked.connect(self._load_users)
        head_row.addWidget(btn_ref)
        layout.addLayout(head_row)

        self.user_table = QTableWidget(0, 7)
        self.user_table.setHorizontalHeaderLabels(
            ["Username", "Full Name", "Email", "Role", "Active", "Registered", "Actions"]
        )
        self._setup_table(self.user_table)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.user_table, stretch=1)

        self.user_status = QLabel("")
        self.user_status.setStyleSheet("font-size: 11px; color: #7A8499;")
        layout.addWidget(self.user_status)
        return widget

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_all(self):
        self._load_dashboard()
        self._load_submissions()
        self._load_reviews()
        self._load_catalog()
        self._load_users()

    def _load_dashboard(self):
        result = self.ctrl.get_dashboard_summary()
        if result["success"]:
            self._populate_dashboard(result["summary"])

    def _load_submissions(self):
        result = self.ctrl.get_pending_submissions()
        subs   = result.get("submissions", [])
        self.sub_table.setRowCount(0)
        for sub in subs:
            row = self.sub_table.rowCount()
            self.sub_table.insertRow(row)
            self.sub_table.setItem(row, 0, QTableWidgetItem(sub.get("title", "")))
            self.sub_table.setItem(row, 1, QTableWidgetItem(sub.get("author", "")))
            self.sub_table.setItem(row, 2, QTableWidgetItem(sub.get("contributor_name", "")))
            date_str = str(sub.get("date_submitted", ""))[:10]
            self.sub_table.setItem(row, 3, QTableWidgetItem(date_str))
            import os
            fname = os.path.basename(sub.get("file_path", "") or "")
            self.sub_table.setItem(row, 4, QTableWidgetItem(fname))
            # Action buttons
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            btn_a = QPushButton("Approve")
            btn_a.setObjectName("btnApprove")
            btn_a.setFixedHeight(26)
            btn_a.clicked.connect(lambda _, s=sub: self._on_approve_submission(s))
            btn_r = QPushButton("Reject")
            btn_r.setObjectName("btnReject")
            btn_r.setFixedHeight(26)
            btn_r.clicked.connect(lambda _, s=sub: self._on_reject_submission(s))
            al.addWidget(btn_a)
            al.addWidget(btn_r)
            self.sub_table.setCellWidget(row, 5, actions)
        self.sub_table.resizeRowsToContents()
        self.sub_status.setText(f"{len(subs)} pending submission(s).")

    def _load_reviews(self):
        result  = self.ctrl.get_pending_reviews()
        reviews = result.get("reviews", [])
        self.rev_table.setRowCount(0)
        for rv in reviews:
            row = self.rev_table.rowCount()
            self.rev_table.insertRow(row)
            self.rev_table.setItem(row, 0, QTableWidgetItem(rv.get("book_title", "")))
            self.rev_table.setItem(row, 1, QTableWidgetItem(rv.get("username", "")))
            self.rev_table.setItem(row, 2, QTableWidgetItem(rv.get("review_text", "")))
            date_str = str(rv.get("date_posted", ""))[:10]
            self.rev_table.setItem(row, 3, QTableWidgetItem(date_str))
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            btn_a = QPushButton("Approve")
            btn_a.setObjectName("btnApprove")
            btn_a.setFixedHeight(26)
            btn_a.clicked.connect(lambda _, r=rv: self._on_approve_review(r))
            btn_r = QPushButton("Reject")
            btn_r.setObjectName("btnReject")
            btn_r.setFixedHeight(26)
            btn_r.clicked.connect(lambda _, r=rv: self._on_reject_review(r))
            al.addWidget(btn_a)
            al.addWidget(btn_r)
            self.rev_table.setCellWidget(row, 4, actions)
        self.rev_table.resizeRowsToContents()
        self.rev_status.setText(f"{len(reviews)} pending review(s).")

    def _load_catalog(self):
        keyword = self.catalog_search.text().strip() or None
        result  = self.ctrl.catalog.search_catalog(keyword=keyword)
        books   = result.get("books", [])
        self.cat_table.setRowCount(0)
        for book in books:
            row = self.cat_table.rowCount()
            self.cat_table.insertRow(row)
            self.cat_table.setItem(row, 0, QTableWidgetItem(book.get("title", "")))
            self.cat_table.setItem(row, 1, QTableWidgetItem(book.get("author", "")))
            self.cat_table.setItem(row, 2, QTableWidgetItem(str(book.get("publication_year") or "—")))
            self.cat_table.setItem(row, 3, QTableWidgetItem(book.get("format_type", "")))
            self.cat_table.setItem(row, 4, QTableWidgetItem(book.get("subject_tags", "") or ""))
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            btn_e = QPushButton("Edit")
            btn_e.setObjectName("btnEdit")
            btn_e.setFixedHeight(26)
            btn_e.clicked.connect(lambda _, b=book: self._on_edit_book(b))
            btn_d = QPushButton("Delete")
            btn_d.setObjectName("btnDelete")
            btn_d.setFixedHeight(26)
            btn_d.clicked.connect(lambda _, b=book: self._on_delete_book(b))
            al.addWidget(btn_e)
            al.addWidget(btn_d)
            self.cat_table.setCellWidget(row, 5, actions)
        self.cat_table.resizeRowsToContents()
        self.cat_status.setText(f"{len(books)} book(s) in catalog.")

    def _load_users(self):
        role_text = self.user_role_filter.currentText()
        role      = None if role_text == "All Roles" else role_text
        result    = self.ctrl.get_all_users(role=role) if self.user.get("role") == "admin" \
                    else (self.ctrl.get_all_patrons() if role == "patron"
                          else self.ctrl.get_all_contributors() if role == "contributor"
                          else self.ctrl.get_all_patrons())
        users = result.get("users", [])
        self.user_table.setRowCount(0)
        for u in users:
            row = self.user_table.rowCount()
            self.user_table.insertRow(row)
            self.user_table.setItem(row, 0, QTableWidgetItem(u.get("username", "")))
            self.user_table.setItem(row, 1, QTableWidgetItem(u.get("full_name", "")))
            self.user_table.setItem(row, 2, QTableWidgetItem(u.get("email", "")))
            self.user_table.setItem(row, 3, QTableWidgetItem(u.get("role", "")))
            active_item = QTableWidgetItem("✓ Active" if u.get("is_active") else "✗ Inactive")
            active_item.setForeground(QColor("#1E7E34") if u.get("is_active") else QColor("#C0392B"))
            self.user_table.setItem(row, 4, active_item)
            date_str = str(u.get("date_registered", ""))[:10]
            self.user_table.setItem(row, 5, QTableWidgetItem(date_str))
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            if u.get("is_active"):
                btn_d = QPushButton("Deactivate")
                btn_d.setObjectName("btnDeactivate")
                btn_d.setFixedHeight(26)
                btn_d.clicked.connect(lambda _, uid=u["user_id"]: self._on_deactivate_user(uid))
                al.addWidget(btn_d)
            else:
                btn_r = QPushButton("Reactivate")
                btn_r.setObjectName("btnReactivate")
                btn_r.setFixedHeight(26)
                btn_r.clicked.connect(lambda _, uid=u["user_id"]: self._on_reactivate_user(uid))
                al.addWidget(btn_r)
            self.user_table.setCellWidget(row, 6, actions)
        self.user_table.resizeRowsToContents()
        self.user_status.setText(f"{len(users)} user(s) shown.")

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _on_approve_submission(self, sub):
        dialog = ApproveSubmissionDialog(sub, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            result = self.ctrl.approve_and_ingest(
                submission_id=sub["submission_id"],
                format_type=data["format_type"],
                subject_tags=data["subject_tags"],
                review_notes=data.get("notes"),
            )
            self._notify(result)
            if result["success"]:
                self._load_all()

    def _on_reject_submission(self, sub):
        notes, ok = self._prompt_notes(f"Reject \"{sub['title']}\"?", "Rejection reason (optional):")
        if ok:
            result = self.ctrl.reject_submission(sub["submission_id"], review_notes=notes or None)
            self._notify(result)
            if result["success"]:
                self._load_submissions()
                self._load_dashboard()

    def _on_approve_review(self, rv):
        result = self.ctrl.approve_review(rv["review_id"])
        self._notify(result)
        if result["success"]:
            self._load_reviews()
            self._load_dashboard()

    def _on_reject_review(self, rv):
        result = self.ctrl.reject_review(rv["review_id"])
        self._notify(result)
        if result["success"]:
            self._load_reviews()

    def _on_add_book(self):
        dialog = BookFormDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            result = self.ctrl.add_book(**data)
            self._notify(result)
            if result["success"]:
                self._load_catalog()
                self._load_dashboard()

    def _on_edit_book(self, book):
        dialog = BookFormDialog(book=book, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            result = self.ctrl.edit_book(book["book_id"], **data)
            self._notify(result)
            if result["success"]:
                self._load_catalog()

    def _on_delete_book(self, book):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete \"{book['title']}\" from the catalog?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            result = self.ctrl.remove_book(book["book_id"])
            self._notify(result)
            if result["success"]:
                self._load_catalog()
                self._load_dashboard()

    def _on_deactivate_user(self, user_id):
        result = self.ctrl.deactivate_user(user_id)
        self._notify(result)
        if result["success"]:
            self._load_users()
            self._load_dashboard()

    def _on_reactivate_user(self, user_id):
        result = self.ctrl.reactivate_user(user_id)
        self._notify(result)
        if result["success"]:
            self._load_users()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _setup_table(self, table):
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)

    def _notify(self, result):
        if result["success"]:
            QMessageBox.information(self, "Success", result["message"])
        else:
            QMessageBox.warning(self, "Error", result["message"])

    def _prompt_notes(self, title, label):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(label))
        text_input = QLineEdit()
        layout.addWidget(text_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        ok = dialog.exec() == QDialog.DialogCode.Accepted
        return text_input.text().strip(), ok


# ------------------------------------------------------------------
# Helper dialogs
# ------------------------------------------------------------------

class ApproveSubmissionDialog(QDialog):
    """Dialog to collect format_type and subject_tags before approving a submission."""

    def __init__(self, submission, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Approve: {submission['title']}")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.combo_format = QComboBox()
        self.combo_format.addItems(["e-book", "print", "thesis", "research paper", "other"])
        layout.addRow("Format Type *", self.combo_format)

        self.input_tags = QLineEdit()
        self.input_tags.setPlaceholderText("e.g. Python, AI, research")
        layout.addRow("Subject Tags", self.input_tags)

        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("Optional notes for the contributor")
        layout.addRow("Notes (optional)", self.input_notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "format_type": self.combo_format.currentText(),
            "subject_tags": self.input_tags.text().strip(),
            "notes": self.input_notes.text().strip(),
        }


class BookFormDialog(QDialog):
    """Dialog for adding or editing a book in the catalog."""

    def __init__(self, book=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Book" if book else "Add Book to Catalog")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.input_title  = QLineEdit(book.get("title", "") if book else "")
        self.input_author = QLineEdit(book.get("author", "") if book else "")
        self.input_year   = QLineEdit(str(book.get("publication_year", "") or "") if book else "")
        self.input_year.setPlaceholderText("e.g. 2023")

        self.combo_format = QComboBox()
        self.combo_format.addItems(["e-book", "print", "thesis", "research paper", "other"])
        if book and book.get("format_type"):
            idx = self.combo_format.findText(book["format_type"])
            if idx >= 0:
                self.combo_format.setCurrentIndex(idx)

        self.input_tags     = QLineEdit(book.get("subject_tags", "") if book else "")
        self.input_abstract = QTextEdit(book.get("abstract", "") if book else "")
        self.input_abstract.setFixedHeight(80)
        self.input_filepath = QLineEdit(book.get("file_path", "") if book else "")
        self.input_filepath.setPlaceholderText("Optional file path or URL")

        layout.addRow("Title *",          self.input_title)
        layout.addRow("Author *",         self.input_author)
        layout.addRow("Publication Year", self.input_year)
        layout.addRow("Format *",         self.combo_format)
        layout.addRow("Subject Tags",     self.input_tags)
        layout.addRow("Abstract",         self.input_abstract)
        layout.addRow("File Path",        self.input_filepath)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        year_text = self.input_year.text().strip()
        return {
            "title":            self.input_title.text().strip(),
            "author":           self.input_author.text().strip(),
            "publication_year": int(year_text) if year_text.isdigit() else None,
            "format_type":      self.combo_format.currentText(),
            "subject_tags":     self.input_tags.text().strip(),
            "abstract":         self.input_abstract.toPlainText().strip(),
            "file_path":        self.input_filepath.text().strip() or None,
        }
