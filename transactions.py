"""
Transactions screen - PySide6 version of the original Tkinter transactions.py.

Entry point is unchanged:  create_transactions_screen(parent=None)
It still uses your existing `database` and `finance_logic` modules.

Changes from the Tkinter version
  * The date field is a QDateEdit. The old code read self.date_var, which was
    commented out, so Add / Update / row-select would have raised AttributeError.
  * mindate=date.today() was removed so past transactions can be entered.
"""

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import database
import finance_logic


class TransactionsScreen(QWidget):
    # Categories are separated by transaction type.
    INCOME_CATEGORIES = [
        "Salary",
        "Business",
        "Investments",
        "Freelance",
        "Benefits",
        "Gifts",
        "Other Income",
    ]

    EXPENSE_CATEGORIES = [
        "Rent",
        "Groceries",
        "Transportation",
        "Utilities",
        "Entertainment",
        "Dining Out",
        "Healthcare",
        "Education",
        "Shopping",
        "Other Expense",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transactions")
        self.selected_transaction_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.create_form())
        layout.addWidget(self.create_search_section())
        layout.addWidget(self.create_transaction_table(), 1)

        self.load_transactions()

    # --------------------------------------------------
    # TRANSACTION FORM
    # --------------------------------------------------

    def create_form(self):
        form = QGroupBox("Transaction Details")
        grid = QGridLayout(form)

        # Transaction type
        grid.addWidget(QLabel("Type:"), 0, 0)
        self.type_box = QComboBox()
        self.type_box.addItems(["expense", "income"])
        grid.addWidget(self.type_box, 0, 1)

        # Category
        grid.addWidget(QLabel("Category:"), 0, 2)
        self.category_box = QComboBox()
        grid.addWidget(self.category_box, 0, 3)

        # Changing the type reloads the category list.
        self.type_box.currentIndexChanged.connect(self.on_type_changed)

        # Amount
        grid.addWidget(QLabel("Amount ($):"), 1, 0)
        self.amount_edit = QLineEdit()
        grid.addWidget(self.amount_edit, 1, 1)

        # Date
        grid.addWidget(QLabel("Date (YYYY-MM-DD):"), 1, 2)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        grid.addWidget(self.date_edit, 1, 3)

        # Description
        grid.addWidget(QLabel("Description:"), 2, 0)
        self.description_edit = QLineEdit()
        grid.addWidget(self.description_edit, 2, 1, 1, 3)

        # Buttons
        buttons = QHBoxLayout()
        for text, slot in [
            ("Add Transaction", self.add_transaction),
            ("Update Selected", self.update_transaction),
            ("Delete Selected", self.delete_transaction),
            ("Clear Form", self.clear_form),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch()
        grid.addLayout(buttons, 3, 0, 1, 4)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # Load the correct category list initially.
        self.on_type_changed()
        return form

    # --------------------------------------------------
    # LINK TYPE AND CATEGORY
    # --------------------------------------------------

    def on_type_changed(self, *_args):
        if self.type_box.currentText().lower() == "income":
            categories = self.INCOME_CATEGORIES
        else:
            categories = self.EXPENSE_CATEGORIES

        current = self.category_box.currentText()

        # Replace the available choices; the first one is selected automatically.
        self.category_box.clear()
        self.category_box.addItems(categories)

        # Keep the previous category if it still belongs to this type.
        if current in categories:
            self.category_box.setCurrentText(current)

    # --------------------------------------------------
    # SEARCH AND FILTER
    # --------------------------------------------------

    def create_search_section(self):
        group = QGroupBox("Search Transactions")
        row = QHBoxLayout(group)

        row.addWidget(QLabel("Description:"))
        self.search_edit = QLineEdit()
        self.search_edit.returnPressed.connect(self.search_transactions)
        row.addWidget(self.search_edit, 1)

        row.addWidget(QLabel("Type:"))
        self.filter_type_box = QComboBox()
        self.filter_type_box.addItems(["All", "Income", "Expense"])
        row.addWidget(self.filter_type_box)

        search = QPushButton("Search")
        search.clicked.connect(self.search_transactions)
        row.addWidget(search)

        show_all = QPushButton("Show All")
        show_all.clicked.connect(self.show_all_transactions)
        row.addWidget(show_all)

        return group

    # --------------------------------------------------
    # TRANSACTION TABLE
    # --------------------------------------------------

    def create_transaction_table(self):
        group = QGroupBox("Transactions")
        inner = QVBoxLayout(group)

        headings = ["ID", "Type", "Amount ($)", "Category", "Date", "Description"]
        widths = [45, 90, 110, 150, 110, 250]

        self.table = QTableWidget(0, len(headings))
        self.table.setHorizontalHeaderLabels(headings)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, width in enumerate(widths):
            self.table.setColumnWidth(i, width)
        self.table.itemSelectionChanged.connect(self.on_select_transaction)

        inner.addWidget(self.table)
        return group

    # --------------------------------------------------
    # FORM VALIDATION
    # --------------------------------------------------

    def get_form_data(self):
        data = {
            "type": self.type_box.currentText().lower(),
            "amount": self.amount_edit.text().strip(),
            "category": self.category_box.currentText().strip(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "description": self.description_edit.text().strip(),
        }

        valid, message = finance_logic.validate_transaction(data)

        if not valid:
            QMessageBox.critical(self, "Invalid Transaction", message)
            return None

        # Confirm that the category belongs to the selected type.
        if data["type"] == "income":
            allowed_categories = self.INCOME_CATEGORIES
        else:
            allowed_categories = self.EXPENSE_CATEGORIES

        if data["category"] not in allowed_categories:
            QMessageBox.critical(
                self, "Invalid Category",
                "Choose a category that matches the transaction type.",
            )
            return None

        data["amount"] = round(float(data["amount"]), 2)
        return data

    # --------------------------------------------------
    # ADD TRANSACTION
    # --------------------------------------------------

    def add_transaction(self):
        data = self.get_form_data()
        if data is None:
            return

        try:
            database.add_transaction(data)
            QMessageBox.information(self, "Success",
                                    "Transaction added successfully.")
            self.clear_form()
            self.load_transactions()
        except Exception as error:
            QMessageBox.critical(
                self, "Database Error",
                f"Could not add transaction:\n{error}",
            )

    # --------------------------------------------------
    # SELECT TRANSACTION FOR EDITING
    # --------------------------------------------------

    def on_select_transaction(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        values = [self.table.item(row, col).text() for col in range(6)]

        self.selected_transaction_id = int(values[0])

        # Set the type first so the correct categories load.
        self.type_box.setCurrentText(values[1].lower())
        self.on_type_changed()

        self.amount_edit.setText(values[2])
        self.category_box.setCurrentText(values[3])
        self.date_edit.setDate(QDate.fromString(values[4], "yyyy-MM-dd"))
        self.description_edit.setText(values[5])

    # --------------------------------------------------
    # UPDATE TRANSACTION
    # --------------------------------------------------

    def update_transaction(self):
        if self.selected_transaction_id is None:
            QMessageBox.warning(self, "No Selection",
                                "Select a transaction from the table first.")
            return

        data = self.get_form_data()
        if data is None:
            return

        try:
            updated = database.update_transaction(
                self.selected_transaction_id, data
            )

            if updated:
                QMessageBox.information(self, "Success",
                                        "Transaction updated successfully.")
            else:
                QMessageBox.warning(self, "Not Found",
                                    "The transaction could not be found.")

            self.clear_form()
            self.load_transactions()
        except Exception as error:
            QMessageBox.critical(
                self, "Database Error",
                f"Could not update transaction:\n{error}",
            )

    # --------------------------------------------------
    # DELETE TRANSACTION
    # --------------------------------------------------

    def delete_transaction(self):
        if self.selected_transaction_id is None:
            QMessageBox.warning(self, "No Selection",
                                "Select a transaction from the table first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this transaction?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            deleted = database.delete_transaction(self.selected_transaction_id)

            if deleted:
                QMessageBox.information(self, "Success",
                                        "Transaction deleted successfully.")

            self.clear_form()
            self.load_transactions()
        except Exception as error:
            QMessageBox.critical(
                self, "Database Error",
                f"Could not delete transaction:\n{error}",
            )

    # --------------------------------------------------
    # SEARCH TRANSACTIONS
    # --------------------------------------------------

    def search_transactions(self):
        filters = {}

        search_text = self.search_edit.text().strip()
        if search_text:
            filters["search"] = search_text

        selected_type = self.filter_type_box.currentText()
        if selected_type == "Income":
            filters["type"] = "income"
        elif selected_type == "Expense":
            filters["type"] = "expense"

        self.load_transactions(filters)

    def show_all_transactions(self):
        self.search_edit.clear()
        self.filter_type_box.setCurrentIndex(0)
        self.load_transactions()

    # --------------------------------------------------
    # LOAD TRANSACTIONS
    # --------------------------------------------------

    def load_transactions(self, filters=None):
        self.table.setRowCount(0)

        transactions = database.get_transactions(filters)

        for transaction in transactions:
            values = (
                transaction["id"],
                transaction["type"].title(),
                f"{float(transaction['amount']):.2f}",
                transaction["category"],
                transaction["date"],
                transaction.get("description", ""),
            )

            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    # --------------------------------------------------
    # CLEAR FORM
    # --------------------------------------------------

    def clear_form(self):
        self.selected_transaction_id = None

        self.type_box.setCurrentText("expense")
        self.on_type_changed()

        self.amount_edit.clear()
        self.date_edit.setDate(QDate.currentDate())
        self.description_edit.clear()
        self.table.clearSelection()


def create_transactions_screen(parent=None):
    return TransactionsScreen(parent)
