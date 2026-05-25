import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QTextEdit, QSplitter, QHeaderView, QAbstractItemView,
    QScrollArea, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QFont, QDesktopServices


class CatalogView(QWidget):
    def __init__(self, catalog_controller, current_user, review_model, on_logout, parent=None):
        super().__init__(parent)
        self.catalog = catalog_controller
        self.user = current_user
        self.review_model = review_model
        self.on_logout = on_logout
        self._books = []

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._load_filter_options()
        self._search()

    def _init_window(self):
        self.setWindowTitle("Libralex — Digital Catalog")
        self.setMinimumSize(950, 620)
        self.setObjectName("CatalogView")
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#CatalogView { background-color: #F7F4EF; }
            QLabel#pageTitle { font-size: 20px; font-weight: 700; color: #1B2A4A; }
            QLabel#userBadge { font-size: 11px; color: #7A8499; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #FFFFFF; border: 1.5px solid #D1C9BC;
                border-radius: 6px; padding: 6px 10px; font-size: 12px; color: #1B2A4A;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color: #3A6BBF; }
            QPushButton { border-radius: 6px; padding: 7px 14px; font-size: 12px; font-weight: 600; }
            QPushButton#btnSearch { background-color: #1B2A4A; color: #FFFFFF; border: none; }
            QPushButton#btnSearch:hover { background-color: #2A3F6F; }
            QPushButton#btnBorrowAction { background-color: #3A6BBF; color: #FFFFFF; border: none; padding: 8px 16px; font-size: 12px; }
            QPushButton#btnBorrowAction:hover { background-color: #4B7FD6; }
            QPushButton#btnPreview { background-color: #F39C12; color: #FFFFFF; border: none; padding: 8px 16px; font-size: 12px; }
            QPushButton#btnPreview:hover { background-color: #D68910; }
            QPushButton#btnSubmitReview { background-color: #1E7E34; color: #FFFFFF; border: none; font-size: 11px; }
            QPushButton#btnSubmitReview:hover { background-color: #218838; }
            QPushButton#btnReset { background-color: transparent; color: #7A8499; border: 1.5px solid #D1C9BC; }
            QPushButton#btnReset:hover { background-color: #EDE8E0; }
            QPushButton#btnLogout { background-color: transparent; color: #C0392B; border: 1.5px solid #F5C6C2; }
            QPushButton#btnLogout:hover { background-color: #FDECEA; }
            QTableWidget { background-color: #FFFFFF; border: 1px solid #E0D9CF; border-radius: 8px; gridline-color: #F0EBE3; selection-background-color: #EAF0FB; }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; }
            QHeaderView::section { background-color: #F0EBE3; color: #4A5568; font-weight: 600; font-size: 11px; padding: 7px 10px; border: none; border-bottom: 1px solid #D1C9BC; }
            QFrame#detailPanel { background-color: #FFFFFF; border: 1px solid #E0D9CF; border-radius: 8px; }
            QLabel#detailTitle { font-size: 15px; font-weight: 700; color: #1B2A4A; }
            QLabel#detailMeta  { font-size: 11px; color: #7A8499; }
            QLabel#sectionHead { font-size: 12px; font-weight: 600; color: #4A5568; }
            QLabel#reviewCount { font-size: 12px; color: #3A6BBF; font-weight: 600; }
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addLayout(self._build_topbar())
        root.addLayout(self._build_search_row())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        self.table = self._build_table()
        splitter.addWidget(self.table)

        # Container Area for Sidebar scroll
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.detail_panel = self._build_detail_panel()
        self.detail_scroll.setWidget(self.detail_panel)
        splitter.addWidget(self.detail_scroll)

        splitter.setSizes([540, 360])
        root.addWidget(splitter, stretch=1)

        self.status_label = QLabel("Loading catalog…")
        self.status_label.setStyleSheet("font-size: 11px; color: #7A8499;")
        root.addWidget(self.status_label)

    def _build_topbar(self):
        row = QHBoxLayout()
        title = QLabel("📚  Digital Catalog")
        title.setObjectName("pageTitle")
        row.addWidget(title)
        row.addStretch()
        user_badge = QLabel(f"Logged in as  {self.user.get('username', '')}  [{self.user.get('role', '').upper()}]")
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
        if self._is_privileged(): cols.append("Actions")

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
        layout.addWidget(placeholder)
        layout.addStretch()

        self._detail_layout = layout
        self._detail_placeholder = placeholder
        return panel

    def _connect_signals(self):
        self.table.cellClicked.connect(self._on_row_clicked)
        self.btn_search.clicked.connect(self._search)
        self.btn_reset.clicked.connect(self._reset_filters)
        self.input_keyword.returnPressed.connect(self._search)

    def _is_privileged(self) -> bool:
        return self.user.get('role', '') in {"librarian", "admin"}

    def _load_filter_options(self):
        result = self.catalog.get_filter_options()
        if not result["success"]: return
        for fmt in result.get("formats", []): self.combo_format.addItem(fmt)
        for year in result.get("years", []): self.combo_year.addItem(str(year))
        for tag in result.get("tags", []): self.combo_tag.addItem(tag)

    def _search(self):
        keyword = self.input_keyword.text().strip() or None
        fmt_text = self.combo_format.currentText()
        year_text = self.combo_year.currentText()
        tag_text = self.combo_tag.currentText()

        format_type = None if fmt_text == "All Formats" else fmt_text
        publication_year = None if year_text == "All Years" else int(year_text)
        subject_tag = None if tag_text == "All Tags" else tag_text

        result = self.catalog.search_catalog(keyword=keyword, publication_year=publication_year,
                                             format_type=format_type, subject_tag=subject_tag)
        self._books = result.get("books", [])
        self._populate_table(self._books)
        self.status_label.setText(result.get("message", ""))

    def _reset_filters(self):
        self.input_keyword.clear()
        self.combo_format.setCurrentIndex(0)
        self.combo_year.setCurrentIndex(0)
        self.combo_tag.setCurrentIndex(0)
        self._search()

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
        self.table.resizeRowsToContents()

    def _on_row_clicked(self, row, _col):
        if row >= len(self._books): return
        book_id = self._books[row]["book_id"]
        result = self.catalog.get_book_details(book_id)
        if result["success"]:
            self._render_detail(result["book"], result["reviews"], result["review_count"])

    def _render_detail(self, book, reviews, review_count):
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        layout = self._detail_layout
        book_id = book["book_id"]

        title_lbl = QLabel(book.get("title", ""))
        title_lbl.setObjectName("detailTitle")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        meta = QLabel(
            f"{book.get('author', '')}  ·  {book.get('publication_year') or '—'}  ·  {book.get('format_type', '')}")
        meta.setObjectName("detailMeta")
        layout.addWidget(meta)

        if book.get("subject_tags"):
            tag_lbl = QLabel(f"🏷  {book['subject_tags']}")
            tag_lbl.setStyleSheet("font-size: 11px; color: #3A6BBF;")
            tag_lbl.setWordWrap(True)
            layout.addWidget(tag_lbl)

        layout.addSpacing(6)

        if book.get("abstract"):
            ab_head = QLabel("Abstract")
            ab_head.setObjectName("sectionHead")
            layout.addWidget(ab_head)
            ab_text = QLabel(book["abstract"])
            ab_text.setWordWrap(True)
            ab_text.setStyleSheet("font-size: 12px; color: #4A5568;")
            layout.addWidget(ab_text)
            layout.addSpacing(6)

        # File Preview Section & Borrow Actions (Stacked side-by-side)
        action_layout = QHBoxLayout()

        if book.get("file_path"):
            preview_btn = QPushButton("📄 Preview Book")
            preview_btn.setObjectName("btnPreview")
            preview_btn.clicked.connect(lambda _, fp=book["file_path"]: self._open_file_preview(fp))
            action_layout.addWidget(preview_btn)

        if not self._is_privileged():
            borrow_btn = QPushButton("🤝 Request to Borrow Book")
            borrow_btn.setObjectName("btnBorrowAction")
            borrow_btn.clicked.connect(lambda _, b_id=book_id: self._execute_borrow_intent(b_id))
            action_layout.addWidget(borrow_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)
        layout.addSpacing(8)

        # Interactive Write-Review Section
        if not self._is_privileged():
            rev_form_head = QLabel("Write a Review")
            rev_form_head.setObjectName("sectionHead")
            layout.addWidget(rev_form_head)

            form_row = QHBoxLayout()
            form_row.addWidget(QLabel("Rating:"))
            self.review_rating_combo = QComboBox()
            self.review_rating_combo.addItems(["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐", "⭐"])
            form_row.addWidget(self.review_rating_combo)
            form_row.addStretch()
            layout.addLayout(form_row)

            self.review_text_input = QTextEdit()
            self.review_text_input.setPlaceholderText("Share your thoughts regarding this book…")
            self.review_text_input.setMaximumHeight(70)
            layout.addWidget(self.review_text_input)

            submit_rev_btn = QPushButton("Submit Review")
            submit_rev_btn.setObjectName("btnSubmitReview")
            submit_rev_btn.clicked.connect(lambda _, b_id=book_id: self._submit_review_action(b_id))
            layout.addWidget(submit_rev_btn)
            layout.addSpacing(10)

        # Displays Public Feed
        rc_lbl = QLabel(f"⭐ {review_count} approved review(s)")
        rc_lbl.setObjectName("reviewCount")
        layout.addWidget(rc_lbl)

        if reviews:
            for rv in reviews[:5]:
                rv_frame = QFrame()
                rv_frame.setStyleSheet("background-color: #F7F4EF; border-radius: 6px; padding: 6px;")
                rv_box = QVBoxLayout(rv_frame)

                # Render calculated numeric star counts
                stars = "★" * rv.get('rating', 5) + "☆" * (5 - rv.get('rating', 5))

                rv_user = QLabel(
                    f"👤 {rv.get('username', 'Patron Reviewer')}   <span style='color: #F39C12;'>{stars}</span>")
                rv_user.setStyleSheet("font-weight: 600; font-size: 11px; color: #1B2A4A;")

                rv_msg = QLabel(rv.get('review_text', ''))
                rv_msg.setWordWrap(True)
                rv_msg.setStyleSheet("font-size: 11px; color: #4A5568;")

                rv_box.addWidget(rv_user)
                rv_box.addWidget(rv_msg)
                layout.addWidget(rv_frame)
        layout.addStretch()

    def _open_file_preview(self, file_path: str):
        """Attempts to open the requested file using the OS default application."""
        if os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            QMessageBox.warning(self, "File Not Found",
                                "The preview file for this book is currently unavailable on the server or the path is broken.")

    def _execute_borrow_intent(self, book_id: int):
        reply = self.catalog.process_borrow_request(book_id)
        if reply.get("success"):
            QMessageBox.information(self, "Request Dispatched", reply.get("message"))
        else:
            QMessageBox.warning(self, "Action Terminated", reply.get("message"))

    def _submit_review_action(self, book_id: int):
        text = self.review_text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Validation Alert", "Review content cannot be submitted empty.")
            return

        # Calculate numeric value based on row indices
        rating_val = 5 - self.review_rating_combo.currentIndex()
        user_id = self.user.get("user_id")

        response = self.review_model.create_review(book_id, user_id, rating_val, text)
        if response["success"]:
            QMessageBox.information(self, "Review Received", response["message"])
            self.review_text_input.clear()
            self.review_rating_combo.setCurrentIndex(0)
            self._search()  # Refresh counters
        else:
            QMessageBox.warning(self, "Submission Stopped", response["message"])