"""
Libralex Information System
views/catalog_view.py

Digital Catalog screen — available to all logged-in roles.
Features:
  - Keyword search bar
  - Filter dropdowns: format, publication year, subject tag
  - Results table with title, author, year, format, review count
  - Book detail panel (opens on row click): abstract, file path, reviews
  - Patrons can submit a review from the detail panel
  - Librarians see an Edit / Delete button per row
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QTextEdit, QSplitter, QHeaderView, QAbstractItemView,
    QScrollArea, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont


class CatalogView(QWidget):
    """
    Digital Catalog view for Libralex.

    Usage:
        catalog_ctrl = CatalogController(conn, current_user)
        review_model = ReviewModel(conn)
        view = CatalogView(
            catalog_controller=catalog_ctrl,
            current_user=auth.current_user,
            review_model=review_model,
        )
        view.show()

    Args:
        catalog_controller: A CatalogController instance.
        current_user:       Dict with at least user_id and role.
        review_model:       ReviewModel instance for patron review submission.
        on_logout:          Callable() — triggered by the logout button.
    """

    def __init__(self, catalog_controller, current_user, review_model, on_logout, parent=None):
        super().__init__(parent)
        self.catalog      = catalog_controller
        self.user         = current_user
        self.review_model = review_model
        self.on_logout    = on_logout
        self._books       = []     # Current search results

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._load_filter_options()
        self._search()             # Load all books on open

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Libralex — Digital Catalog")
        self.setMinimumSize(900, 620)
        self.setObjectName("CatalogView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#CatalogView { background-color: #F7F4EF; }
            QLabel#pageTitle { font-size: 20px; font-weight: 700; color: #1B2A4A; }
            QLabel#userBadge { font-size: 11px; color: #7A8499; }
            QLineEdit, QComboBox {
                background-color: #FFFFFF; border: 1.5px solid #D1C9BC;
                border-radius: 6px; padding: 6px 10px; font-size: 12px; color: #1B2A4A;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #3A6BBF; }
            QPushButton#btnSearch {
                background-color: #1B2A4A; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 7px 18px; font-size: 12px; font-weight: 600;
            }
            QPushButton#btnSearch:hover { background-color: #2A3F6F; }
            QPushButton#btnReset {
                background-color: transparent; color: #7A8499;
                border: 1.5px solid #D1C9BC; border-radius: 6px; padding: 7px 14px; font-size: 12px;
            }
            QPushButton#btnReset:hover { background-color: #EDE8E0; }
            QPushButton#btnLogout {
                background-color: transparent; color: #C0392B;
                border: 1.5px solid #F5C6C2; border-radius: 6px; padding: 6px 14px; font-size: 12px;
            }
            QPushButton#btnLogout:hover { background-color: #FDECEA; }
            QPushButton#btnSubmitReview {
                background-color: #1B2A4A; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 8px 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton#btnSubmitReview:hover { background-color: #2A3F6F; }
            QPushButton#btnEditBook {
                background-color: #E8F0FE; color: #1B2A4A; border: 1px solid #BDD0F8;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton#btnDeleteBook {
                background-color: #FDECEA; color: #C0392B; border: 1px solid #F5C6C2;
                border-radius: 5px; padding: 4px 10px; font-size: 11px;
            }
            QTableWidget {
                background-color: #FFFFFF; border: 1px solid #E0D9CF;
                border-radius: 8px; gridline-color: #F0EBE3;
                selection-background-color: #EAF0FB;
            }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; }
            QTableWidget::item:selected { background-color: #D6E4F7; color: #1B2A4A; }
            QHeaderView::section {
                background-color: #F0EBE3; color: #4A5568;
                font-weight: 600; font-size: 11px;
                padding: 7px 10px; border: none; border-bottom: 1px solid #D1C9BC;
            }
            QFrame#detailPanel {
                background-color: #FFFFFF; border: 1px solid #E0D9CF; border-radius: 8px;
            }
            QTextEdit {
                background-color: #F7F4EF; border: 1.5px solid #D1C9BC;
                border-radius: 6px; padding: 6px; font-size: 12px; color: #1B2A4A;
            }
            QLabel#detailTitle { font-size: 15px; font-weight: 700; color: #1B2A4A; }
            QLabel#detailMeta  { font-size: 11px; color: #7A8499; }
            QLabel#sectionHead { font-size: 12px; font-weight: 600; color: #4A5568; }
            QLabel#reviewCount { font-size: 12px; color: #3A6BBF; font-weight: 600; }
            QLabel#errorLabel  {
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

        # Top bar
        root.addLayout(self._build_topbar())

        # Search + filter row
        root.addLayout(self._build_search_row())

        # Splitter: table (left) | detail panel (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        self.table = self._build_table()
        splitter.addWidget(self.table)

        self.detail_panel = self._build_detail_panel()
        splitter.addWidget(self.detail_panel)

        splitter.setSizes([560, 340])
        root.addWidget(splitter, stretch=1)

        # Status bar
        self.status_label = QLabel("Loading catalog…")
        self.status_label.setStyleSheet("font-size: 11px; color: #7A8499;")
        root.addWidget(self.status_label)

    def _build_topbar(self):
        row = QHBoxLayout()
        title = QLabel("📚  Digital Catalog")
        title.setObjectName("pageTitle")
        row.addWidget(title)
        row.addStretch()
        user_badge = QLabel(
            f"Logged in as  {self.user.get('username', '')}  "
            f"[{self.user.get('role', '').upper()}]"
        )
        user_badge.setObjectName("userBadge")
        row.addWidget(user_badge)
        row.addSpacing(12)
        btn_logout = QPushButton("Logout")
        btn_logout.setObjectName("btnLogout")
        btn_logout.clicked.connect(self.on_logout)
        row.addWidget(btn_logout)
        return row

    def _build_search_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        self.input_keyword = QLineEdit()
        self.input_keyword.setPlaceholderText("Search by title, author, or keyword…")
        self.input_keyword.setFixedHeight(34)
        row.addWidget(self.input_keyword, 3)

        self.combo_format = QComboBox()
        self.combo_format.setFixedHeight(34)
        self.combo_format.addItem("All Formats")
        row.addWidget(self.combo_format, 1)

        self.combo_year = QComboBox()
        self.combo_year.setFixedHeight(34)
        self.combo_year.addItem("All Years")
        row.addWidget(self.combo_year, 1)

        self.combo_tag = QComboBox()
        self.combo_tag.setFixedHeight(34)
        self.combo_tag.addItem("All Tags")
        row.addWidget(self.combo_tag, 1)

        self.btn_search = QPushButton("Search")
        self.btn_search.setObjectName("btnSearch")
        self.btn_search.setFixedHeight(34)
        row.addWidget(self.btn_search)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("btnReset")
        self.btn_reset.setFixedHeight(34)
        row.addWidget(self.btn_reset)

        return row

    def _build_table(self):
        cols = ["Title", "Author", "Year", "Format", "Reviews"]
        if self._is_privileged():
            cols.append("Actions")

        table = QTableWidget(0, len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.setShowGrid(False)
        return table

    def _build_detail_panel(self):
        panel = QFrame()
        panel.setObjectName("detailPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        placeholder = QLabel("Select a resource to view details.")
        placeholder.setObjectName("detailMeta")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)
        layout.addStretch()

        self._detail_layout = layout
        self._detail_placeholder = placeholder
        return panel

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.btn_search.clicked.connect(self._search)
        self.btn_reset.clicked.connect(self._reset_filters)
        self.table.cellClicked.connect(self._on_row_clicked)
        self.input_keyword.returnPressed.connect(self._search)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_filter_options(self):
        result = self.catalog.get_filter_options()
        if not result["success"]:
            return

        for fmt in result.get("formats", []):
            self.combo_format.addItem(fmt)
        for year in result.get("years", []):
            self.combo_year.addItem(str(year))
        for tag in result.get("tags", []):
            self.combo_tag.addItem(tag)

    def _search(self):
        keyword     = self.input_keyword.text().strip() or None
        fmt_text    = self.combo_format.currentText()
        year_text   = self.combo_year.currentText()
        tag_text    = self.combo_tag.currentText()

        format_type      = None if fmt_text  == "All Formats" else fmt_text
        publication_year = None if year_text == "All Years"   else int(year_text)
        subject_tag      = None if tag_text  == "All Tags"    else tag_text

        result = self.catalog.search_catalog(
            keyword=keyword,
            publication_year=publication_year,
            format_type=format_type,
            subject_tag=subject_tag,
        )

        self._books = result.get("books", [])
        self._populate_table(self._books)
        self.status_label.setText(result.get("message", ""))

    def _reset_filters(self):
        self.input_keyword.clear()
        self.combo_format.setCurrentIndex(0)
        self.combo_year.setCurrentIndex(0)
        self.combo_tag.setCurrentIndex(0)
        self._search()

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_table(self, books):
        self.table.setRowCount(0)
        for book in books:
            row = self.table.rowCount()
            self.table.insertRow(row)

            review_count = self.catalog.review_model.get_review_count_by_book(book["book_id"])

            self.table.setItem(row, 0, QTableWidgetItem(book.get("title", "")))
            self.table.setItem(row, 1, QTableWidgetItem(book.get("author", "")))
            self.table.setItem(row, 2, QTableWidgetItem(str(book.get("publication_year") or "—")))
            self.table.setItem(row, 3, QTableWidgetItem(book.get("format_type", "")))
            self.table.setItem(row, 4, QTableWidgetItem(f"⭐ {review_count}"))

            # Librarian action buttons
            if self._is_privileged():
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 2, 4, 2)
                action_layout.setSpacing(6)

                btn_edit = QPushButton("Edit")
                btn_edit.setObjectName("btnEditBook")
                btn_edit.setFixedHeight(26)
                btn_edit.clicked.connect(lambda _, b=book: self._on_edit_book(b))

                btn_del = QPushButton("Delete")
                btn_del.setObjectName("btnDeleteBook")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, b=book: self._on_delete_book(b))

                action_layout.addWidget(btn_edit)
                action_layout.addWidget(btn_del)
                self.table.setCellWidget(row, 5, action_widget)

        self.table.resizeRowsToContents()

    # ------------------------------------------------------------------
    # Detail panel
    # ------------------------------------------------------------------

    def _on_row_clicked(self, row, _col):
        if row >= len(self._books):
            return
        book_id = self._books[row]["book_id"]
        result  = self.catalog.get_book_details(book_id)
        if result["success"]:
            self._render_detail(result["book"], result["reviews"], result["review_count"])

    def _render_detail(self, book, reviews, review_count):
        # Clear existing detail widgets
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        layout = self._detail_layout

        # Title
        title_lbl = QLabel(book.get("title", ""))
        title_lbl.setObjectName("detailTitle")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        # Meta
        meta = QLabel(
            f"{book.get('author', '')}  ·  "
            f"{book.get('publication_year') or '—'}  ·  "
            f"{book.get('format_type', '')}"
        )
        meta.setObjectName("detailMeta")
        layout.addWidget(meta)

        # Tags
        if book.get("subject_tags"):
            tag_lbl = QLabel(f"🏷  {book['subject_tags']}")
            tag_lbl.setStyleSheet("font-size: 11px; color: #3A6BBF;")
            tag_lbl.setWordWrap(True)
            layout.addWidget(tag_lbl)

        layout.addSpacing(6)

        # Abstract
        if book.get("abstract"):
            ab_head = QLabel("Abstract")
            ab_head.setObjectName("sectionHead")
            layout.addWidget(ab_head)
            ab_text = QLabel(book["abstract"])
            ab_text.setWordWrap(True)
            ab_text.setStyleSheet("font-size: 12px; color: #4A5568;")
            layout.addWidget(ab_text)
            layout.addSpacing(6)

        # Review count
        rc_lbl = QLabel(f"⭐ {review_count} approved review(s)")
        rc_lbl.setObjectName("reviewCount")
        layout.addWidget(rc_lbl)

        # Reviews list
        if reviews:
            for rv in reviews[:5]:   # Show latest 5
                rv_frame = QFrame()
                rv_frame.setStyleSheet(
                    "QFrame { background:#F7F4EF; border-radius:6px; padding:4px; }"
                )
                rv_layout = QVBoxLayout(rv_frame)
                rv_layout.setContentsMargins(8, 6, 8, 6)
                rv_layout.setSpacing(2)
                rv_user = QLabel(f"@{rv.get('username', 'unknown')}")
                rv_user.setStyleSheet("font-size: 11px; font-weight: 600; color: #1B2A4A;")
                rv_text = QLabel(rv.get("review_text", ""))
                rv_text.setWordWrap(True)
                rv_text.setStyleSheet("font-size: 11px; color: #4A5568;")
                rv_layout.addWidget(rv_user)
                rv_layout.addWidget(rv_text)
                layout.addWidget(rv_frame)

        layout.addSpacing(8)

        # Patron: submit review
        if self.user.get("role") == "patron":
            rev_head = QLabel("Submit a Review")
            rev_head.setObjectName("sectionHead")
            layout.addWidget(rev_head)

            self._review_input = QTextEdit()
            self._review_input.setPlaceholderText("Write your review here…")
            self._review_input.setFixedHeight(70)
            layout.addWidget(self._review_input)

            self._review_feedback = QLabel("")
            self._review_feedback.setWordWrap(True)
            self._review_feedback.hide()
            layout.addWidget(self._review_feedback)

            btn_rev = QPushButton("Submit Review")
            btn_rev.setObjectName("btnSubmitReview")
            btn_rev.clicked.connect(lambda: self._on_submit_review(book["book_id"]))
            layout.addWidget(btn_rev)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_submit_review(self, book_id):
        text = self._review_input.toPlainText().strip()
        if not text:
            self._set_review_feedback("Review text cannot be empty.", error=True)
            return

        result = self.review_model.create_review(
            book_id=book_id,
            user_id=self.user["user_id"],
            review_text=text,
        )
        if result["success"]:
            self._review_input.clear()
            self._set_review_feedback("Review submitted! Pending librarian approval.", error=False)
        else:
            self._set_review_feedback(result["message"], error=True)

    def _set_review_feedback(self, msg, error=True):
        obj = "errorLabel" if error else "successLabel"
        prefix = "⚠  " if error else "✓  "
        self._review_feedback.setObjectName(obj)
        self._review_feedback.setStyleSheet(
            "color:#C0392B;background:#FDECEA;border:1px solid #F5C6C2;"
            "border-radius:5px;padding:5px 8px;font-size:11px;" if error else
            "color:#1E7E34;background:#E9F7EC;border:1px solid #A8D5B0;"
            "border-radius:5px;padding:5px 8px;font-size:11px;"
        )
        self._review_feedback.setText(prefix + msg)
        self._review_feedback.show()

    def _on_edit_book(self, book):
        # Placeholder: open an EditBookDialog (to be implemented)
        QMessageBox.information(self, "Edit Book",
            f"Edit dialog for:\n\"{book['title']}\"\n\n(EditBookDialog — coming soon)")

    def _on_delete_book(self, book):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete \"{book['title']}\" from the catalog?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            result = self.catalog.remove_book(book["book_id"])
            if result["success"]:
                self._search()
                QMessageBox.information(self, "Deleted", result["message"])
            else:
                QMessageBox.warning(self, "Error", result["message"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_privileged(self):
        return self.user.get("role") in {"librarian", "admin"}
