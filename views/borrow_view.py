from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, \
    QMessageBox


class BorrowView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Library Transactions")
        self.resize(800, 400)  # Give the pop-up window a good default size

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.title_label = QLabel("Library Transactions")
        self.layout.addWidget(self.title_label)

        self.borrow_table = QTableWidget()
        self.layout.addWidget(self.borrow_table)

        self.actions_layout = QHBoxLayout()
        self.layout.addLayout(self.actions_layout)

        self.refresh_button = QPushButton("Refresh Data Ledger")
        self.actions_layout.addWidget(self.refresh_button)

        self.approve_btn = QPushButton("Approve Selection")
        self.reject_btn = QPushButton("Reject Selection")
        self.approve_btn.setVisible(False)
        self.reject_btn.setVisible(False)
        self.actions_layout.addWidget(self.approve_btn)
        self.actions_layout.addWidget(self.reject_btn)

    def setup_user_table(self):
        self.setWindowTitle("My Borrowed & Pending Books")
        self.title_label.setText("My Borrowed Books")
        self.borrow_table.setColumnCount(5)
        self.borrow_table.setHorizontalHeaderLabels(
            ["Title", "Author", "Date Requested/Borrowed", "Due Date", "Status"])
        self.approve_btn.setVisible(False)
        self.reject_btn.setVisible(False)

    def setup_admin_table(self):
        self.setWindowTitle("Master Loan Ledger Queue")
        self.title_label.setText("Master Loan Ledger Queue")
        self.borrow_table.setColumnCount(7)
        self.borrow_table.setHorizontalHeaderLabels(
            ["Request ID", "Book Title", "Patron Name", "Email Address", "Requested Date", "Due Window", "Status"])
        self.approve_btn.setVisible(True)
        self.reject_btn.setVisible(True)

    def populate_table(self, data: list, role: str):
        self.borrow_table.setRowCount(0)
        for row_idx, row_data in enumerate(data):
            self.borrow_table.insertRow(row_idx)
            if role == "user":
                self.borrow_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['title'])))
                self.borrow_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data['author'])))
                self.borrow_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data['borrow_date'])))
                self.borrow_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data['due_date'])))
                self.borrow_table.setItem(row_idx, 4, QTableWidgetItem(str(row_data['status']).upper()))
            elif role == "admin":
                self.borrow_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data['borrow_id'])))
                self.borrow_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data['title'])))
                self.borrow_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data['full_name'])))
                self.borrow_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data['email'])))
                self.borrow_table.setItem(row_idx, 4, QTableWidgetItem(str(row_data['borrow_date'])))
                self.borrow_table.setItem(row_idx, 5, QTableWidgetItem(str(row_data['due_date'])))
                self.borrow_table.setItem(row_idx, 6, QTableWidgetItem(str(row_data['status']).upper()))

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)