from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, \
    QMessageBox, QAbstractItemView, QHeaderView
from PyQt6.QtCore import Qt


class BorrowView(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("BorrowView")
        self.setWindowTitle("Library Transactions")
        self.resize(850, 450)
        self._apply_styles()

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 16, 20, 16)
        self.layout.setSpacing(12)
        self.setLayout(self.layout)

        self.title_label = QLabel("Library Transactions")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #1B2A4A;")
        self.layout.addWidget(self.title_label)

        self.borrow_table = QTableWidget()
        self.borrow_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.borrow_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.borrow_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.borrow_table.setAlternatingRowColors(True)
        self.borrow_table.verticalHeader().setVisible(False)
        self.borrow_table.setShowGrid(False)
        self.layout.addWidget(self.borrow_table)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)
        self.layout.addLayout(self.actions_layout)

        # Interactive Rounded Action Handles
        self.refresh_button = QPushButton("Refresh Data Ledger")
        self.refresh_button.setObjectName("btnPrimary")

        self.approve_btn = QPushButton("Approve Selection")
        self.approve_btn.setObjectName("btnSuccess")

        self.reject_btn = QPushButton("Reject Selection")
        self.reject_btn.setObjectName("btnDanger")

        self.return_btn = QPushButton("Mark as Returned")
        self.return_btn.setObjectName("btnSecondary")

        # Hide actions until administrative access mode is confirmed
        self.approve_btn.setVisible(False)
        self.reject_btn.setVisible(False)
        self.return_btn.setVisible(False)

        self.actions_layout.addWidget(self.refresh_button)
        self.actions_layout.addWidget(self.approve_btn)
        self.actions_layout.addWidget(self.reject_btn)
        self.actions_layout.addWidget(self.return_btn)
        self.actions_layout.addStretch()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget#BorrowView { background-color: #F7F4EF; }
            QTableWidget {
                background-color: #FFFFFF; border: 1px solid #E0D9CF;
                border-radius: 8px; gridline-color: #F0EBE3;
                selection-background-color: #EAF0FB;
            }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; font-size: 12px; }
            QTableWidget::item:selected { background-color: #D6E4F7; color: #1B2A4A; }
            QHeaderView::section {
                background-color: #F0EBE3; color: #4A5568;
                font-weight: 600; font-size: 11px;
                padding: 7px 10px; border: none; border-bottom: 1px solid #D1C9BC;
            }
            QPushButton {
                border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: 600; min-height: 18px;
            }
            QPushButton#btnPrimary { background-color: #1B2A4A; color: #FFFFFF; border: none; }
            QPushButton#btnPrimary:hover { background-color: #2A3F6F; }

            QPushButton#btnSecondary { background-color: #3A6BBF; color: #FFFFFF; border: none; }
            QPushButton#btnSecondary:hover { background-color: #4B7FD6; }

            QPushButton#btnSuccess { background-color: #1E7E34; color: #FFFFFF; border: none; }
            QPushButton#btnSuccess:hover { background-color: #28a745; }

            QPushButton#btnDanger { background-color: #C0392B; color: #FFFFFF; border: none; }
            QPushButton#btnDanger:hover { background-color: #E74C3C; }
        """)

    def setup_user_table(self):
        self.setWindowTitle("My Borrowed Books")
        self.title_label.setText("My Active Borrowed Books")
        self.borrow_table.setColumnCount(4)
        self.borrow_table.setHorizontalHeaderLabels(["Title", "Author", "Date Borrowed", "Due Date"])
        self.borrow_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.approve_btn.setVisible(False)
        self.reject_btn.setVisible(False)
        self.return_btn.setVisible(False)

    def setup_admin_table(self):
        self.setWindowTitle("Master Loan Ledger Queue")
        self.title_label.setText("Master Loan Ledger Queue")
        self.borrow_table.setColumnCount(7)
        self.borrow_table.setHorizontalHeaderLabels(
            ["ID", "Book Title", "Patron Name", "Email Address", "Borrowed/Requested Date", "Return Due Window",
             "Status"]
        )
        self.borrow_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.borrow_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.approve_btn.setVisible(True)
        self.reject_btn.setVisible(True)
        self.return_btn.setVisible(True)

    def populate_table(self, data: list, role: str):
        self.borrow_table.setRowCount(0)
        for row_idx, row_data in enumerate(data):
            self.borrow_table.insertRow(row_idx)
            if role == "patron":
                self.borrow_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['title'])))
                self.borrow_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data['author'])))
                self.borrow_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data['borrow_date'])))
                self.borrow_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data['due_date'])))
            elif role in ["admin", "librarian"]:
                self.borrow_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['borrow_id'])))
                self.borrow_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data['title'])))
                self.borrow_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data['full_name'])))
                self.borrow_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data['email'])))
                self.borrow_table.setItem(row_idx, 4, QTableWidgetItem(str(row_data['borrow_date'])))
                due = str(row_data['due_date']) if row_data['status'] == 'borrowed' else "PENDING APPROVAL"
                self.borrow_table.setItem(row_idx, 5, QTableWidgetItem(due))
                self.borrow_table.setItem(row_idx, 6, QTableWidgetItem(str(row_data['status']).upper()))
        self.borrow_table.resizeRowsToContents()

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)