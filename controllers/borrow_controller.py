from models.borrow_model import BorrowModel
from views.borrow_view import BorrowView


class BorrowController:
    def __init__(self, conn, current_user_id=None, role="user"):
        self.model = BorrowModel(conn)
        self.view = BorrowView()

        self.current_user_id = current_user_id
        self.role = role

        if self.role == "user":
            self.view.setup_user_table()
        elif self.role == "admin":
            self.view.setup_admin_table()
            self.view.approve_btn.clicked.connect(self.process_approval)
            self.view.reject_btn.clicked.connect(self.process_rejection)

        self.view.refresh_button.clicked.connect(self.load_data)
        self.load_data()

    def load_data(self):
        if self.role == "user" and self.current_user_id:
            data = self.model.get_user_borrows(self.current_user_id)
            self.view.populate_table(data, role="user")
        elif self.role == "admin":
            data = self.model.get_all_borrows()
            self.view.populate_table(data, role="admin")

    def execute_checkout_request(self, book_id: int):
        if self.role == "user" and self.current_user_id:
            result = self.model.borrow_book(self.current_user_id, book_id)
            self.view.show_message("Request Status", result["message"])
            self.load_data()

    def get_selected_borrow_id(self) -> int:
        current_row = self.view.borrow_table.currentRow()
        if current_row < 0:
            self.view.show_message("Selection Error", "Please click on a row first.")
            return None
        id_item = self.view.borrow_table.item(current_row, 0)
        return int(id_item.text()) if id_item else None

    def process_approval(self):
        borrow_id = self.get_selected_borrow_id()
        if borrow_id is not None:
            if self.model.approve_borrow(borrow_id):
                self.view.show_message("Success", "Loan request approved.")
                self.load_data()
            else:
                self.view.show_message("Error", "Could not approve. Ensure it is currently 'PENDING'.")

    def process_rejection(self):
        borrow_id = self.get_selected_borrow_id()
        if borrow_id is not None:
            if self.model.reject_borrow(borrow_id):
                self.view.show_message("Rejected", "Loan request rejected.")
                self.load_data()
            else:
                self.view.show_message("Error", "Could not reject. Ensure it is currently 'PENDING'.")