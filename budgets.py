"""
Budgets screen - PySide6 version of the original Tkinter budgets.py.

Entry point is unchanged:  create_budgets_screen(parent=None)
It still uses your existing `database` and `finance_logic` modules.
"""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import database
import finance_logic

CATEGORIES = [
    "Rent", "Groceries", "Transportation", "Utilities",
    "Entertainment", "Healthcare", "Education", "Other",
]

RED = "#c62828"


class BudgetsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monthly Budgets")
        self.selected_budget_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.create_form())
        layout.addWidget(self.create_budget_table(), 1)

        self.load_budgets()

    # ---------------- FORM ----------------

    def create_form(self):
        form = QGroupBox("Monthly Budget")
        grid = QGridLayout(form)

        # Month picker (replaces the DateEdit + month text box of the Tkinter version)
        grid.addWidget(QLabel("Month (YYYY-MM):"), 0, 0)
        self.month_edit = QDateEdit(QDate.currentDate())
        self.month_edit.setDisplayFormat("yyyy-MM")
        self.month_edit.setCalendarPopup(True)
        self.month_edit.dateChanged.connect(self.load_budgets)
        grid.addWidget(self.month_edit, 0, 1)

        grid.addWidget(QLabel("Category:"), 0, 2)
        self.category_box = QComboBox()
        self.category_box.addItems(CATEGORIES)
        self.category_box.setPlaceholderText("Select category")
        self.category_box.setCurrentIndex(-1)
        grid.addWidget(self.category_box, 0, 3)

        grid.addWidget(QLabel("Budget Limit ($):"), 1, 0)
        self.limit_edit = QLineEdit()
        grid.addWidget(self.limit_edit, 1, 1)

        buttons = QHBoxLayout()
        for text, slot in [
            ("Add Budget", self.add_budget),
            ("Update Selected", self.update_budget),
            ("Delete Selected", self.delete_budget),
            ("Clear Form", self.clear_form),
            ("Load Month", self.load_budgets),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch()
        grid.addLayout(buttons, 2, 0, 1, 4)

        return form

    # ---------------- TABLE ----------------

    def create_budget_table(self):
        group = QGroupBox("Budget Overview")
        inner = QVBoxLayout(group)

        headings = ["ID", "Category", "Budget Limit", "Amount Spent",
                    "Remaining", "Status"]
        widths = [50, 160, 130, 130, 130, 120]

        self.table = QTableWidget(0, len(headings))
        self.table.setHorizontalHeaderLabels(headings)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, width in enumerate(widths):
            self.table.setColumnWidth(i, width)
        self.table.itemSelectionChanged.connect(self.on_select_budget)

        inner.addWidget(self.table)
        return group

    # ---------------- FORM DATA ----------------

    def current_month(self):
        return self.month_edit.date().toString("yyyy-MM")

    def get_form_data(self):
        month = self.current_month()
        category = self.category_box.currentText().strip()
        amount_text = self.limit_edit.text().strip()

        # Validate the month.
        try:
            date.fromisoformat(month + "-01")
            if len(month) != 7:
                raise ValueError
        except ValueError:
            QMessageBox.critical(
                self, "Invalid Month",
                "Enter the month in YYYY-MM format, for example 2026-10.",
            )
            return None

        if not category:
            QMessageBox.critical(self, "Missing Category",
                                 "Please select a category.")
            return None

        valid, message = finance_logic.validate_amount(amount_text)
        if not valid:
            QMessageBox.critical(self, "Invalid Budget", message)
            return None

        return {
            "month": month,
            "category": category,
            "limit_amount": round(float(amount_text), 2),
        }

    # ---------------- ACTIONS ----------------

    def add_budget(self):
        data = self.get_form_data()
        if data is None:
            return

        try:
            database.add_budget(data)
            QMessageBox.information(self, "Success", "Budget added successfully.")
            self.clear_form()
            self.load_budgets()
        except Exception as error:
            QMessageBox.critical(
                self, "Could Not Add Budget",
                "This category may already have a budget "
                "for the selected month.\n\n" + str(error),
            )

    def update_budget(self):
        if self.selected_budget_id is None:
            QMessageBox.warning(self, "No Selection",
                                "Select a budget from the table first.")
            return

        data = self.get_form_data()
        if data is None:
            return

        try:
            updated = database.update_budget(self.selected_budget_id, data)

            if updated:
                QMessageBox.information(self, "Success",
                                        "Budget updated successfully.")
            else:
                QMessageBox.warning(self, "Not Found",
                                    "The selected budget no longer exists.")

            self.clear_form()
            self.load_budgets()
        except Exception as error:
            QMessageBox.critical(
                self, "Could Not Update Budget",
                "Check whether this category already has "
                "a budget for the selected month.\n\n" + str(error),
            )

    def delete_budget(self):
        if self.selected_budget_id is None:
            QMessageBox.warning(self, "No Selection",
                                "Select a budget from the table first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this budget?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            database.delete_budget(self.selected_budget_id)
            QMessageBox.information(self, "Success",
                                    "Budget deleted successfully.")
            self.clear_form()
            self.load_budgets()
        except Exception as error:
            QMessageBox.critical(self, "Database Error", str(error))

    def on_select_budget(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        self.selected_budget_id = int(self.table.item(row, 0).text())

        self.category_box.setCurrentText(self.table.item(row, 1).text())
        self.limit_edit.setText(self.table.item(row, 2).text())

    def load_budgets(self, *_args):
        month = self.current_month()

        self.table.setRowCount(0)

        budgets = database.get_budgets(month)

        # Retrieve expenses for the selected month.
        transactions = database.get_transactions({
            "type": "expense",
            "start_date": month + "-01",
            "end_date": month + "-31",
        })

        spending = finance_logic.calculate_category_spending(transactions, month)

        for budget in budgets:
            category = budget["category"]
            limit = float(budget["limit_amount"])
            spent = spending.get(category, 0.0)

            remaining = finance_logic.calculate_budget_remaining(limit, spent)
            status = finance_logic.get_budget_status(limit, spent)

            values = (
                budget["id"],
                category,
                f"{limit:.2f}",
                f"{spent:.2f}",
                f"{remaining:.2f}",
                status.title(),
            )

            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                # Highlight over-budget rows (negative remaining) in red.
                if remaining < 0 and column >= 4:
                    item.setForeground(QColor(RED))
                self.table.setItem(row, column, item)

    def clear_form(self):
        self.selected_budget_id = None
        self.category_box.setCurrentIndex(-1)
        self.limit_edit.clear()
        self.table.clearSelection()


def create_budgets_screen(parent=None):
    return BudgetsScreen(parent)
