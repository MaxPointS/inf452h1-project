

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QDateEdit, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

# PySide6 is imported first so matplotlib picks the PySide6 binding.
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import database
import finance_logic


class DashboardScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Financial Dashboard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(self.create_header())
        layout.addLayout(self.create_summary_cards())
        layout.addLayout(self.create_charts(), 1)
        layout.addWidget(self.create_recent_transactions())

        self.refresh_dashboard()

    # ---------------- HEADER ----------------

    def create_header(self):
        header = QHBoxLayout()

        title = QLabel("Financial Dashboard")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)

        header.addSpacing(20)
        header.addWidget(QLabel("Month (YYYY-MM):"))

        self.month_edit = QDateEdit(QDate.currentDate())
        self.month_edit.setDisplayFormat("yyyy-MM")
        self.month_edit.setCalendarPopup(True)
        self.month_edit.dateChanged.connect(self.refresh_dashboard)
        header.addWidget(self.month_edit)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_dashboard)
        header.addWidget(refresh)

        header.addStretch()
        return header

    # ---------------- SUMMARY CARDS ----------------

    def create_summary_cards(self):
        cards = QHBoxLayout()
        self.income_label = self.create_card(cards, "Total Income")
        self.expenses_label = self.create_card(cards, "Total Expenses")
        self.balance_label = self.create_card(cards, "Remaining Balance")
        return cards

    @staticmethod
    def create_card(parent_layout, title):
        box = QGroupBox(title)
        inner = QVBoxLayout(box)

        label = QLabel("$0.00")
        label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(15)
        font.setBold(True)
        label.setFont(font)

        inner.addWidget(label)
        parent_layout.addWidget(box, 1)
        return label

    # ---------------- CHARTS ----------------

    def create_charts(self):
        row = QHBoxLayout()

        # Left chart: expenses by category
        self.expense_figure = Figure(figsize=(3, 3), dpi=100)
        self.expense_axis = self.expense_figure.add_subplot(111)
        self.expense_canvas = FigureCanvasQTAgg(self.expense_figure)
        self.expense_canvas.setMinimumHeight(200)
        row.addWidget(self.expense_canvas, 1)

        # Right chart: income versus expenses
        self.comparison_figure = Figure(figsize=(3, 3), dpi=100)
        self.comparison_axis = self.comparison_figure.add_subplot(111)
        self.comparison_canvas = FigureCanvasQTAgg(self.comparison_figure)
        self.comparison_canvas.setMinimumHeight(200)
        row.addWidget(self.comparison_canvas, 1)

        return row

    def update_expense_chart(self, spending):
        self.expense_axis.clear()

        # Remove categories with zero spending.
        spending = {
            category: amount
            for category, amount in spending.items()
            if amount > 0
        }

        if spending:
            self.expense_axis.pie(
                list(spending.values()),
                labels=list(spending.keys()),
                autopct="%1.1f%%",
                startangle=90,
            )
        else:
            self.expense_axis.text(
                0.5, 0.5, "No expenses recorded",
                ha="center", va="center",
                transform=self.expense_axis.transAxes,
            )

        self.expense_axis.set_title("Expenses by Category")
        self.expense_figure.tight_layout()
        self.expense_canvas.draw()

    def update_comparison_chart(self, income, expenses):
        self.comparison_axis.clear()

        labels = ["Income", "Expenses"]
        values = [income, expenses]

        bars = self.comparison_axis.bar(labels, values)
        self.comparison_axis.set_title("Income vs Expenses")
        self.comparison_axis.set_ylabel("Amount ($)")
        self.comparison_axis.set_ylim(
            bottom=0, top=max(income, expenses, 1) * 1.2
        )

        # Display the amount above each bar.
        for bar, amount in zip(bars, values):
            self.comparison_axis.annotate(
                f"${amount:,.2f}",
                (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                ha="center", va="bottom",
                xytext=(0, 4), textcoords="offset points",
                fontsize=9,
            )

        self.comparison_figure.tight_layout()
        self.comparison_canvas.draw()

    # ---------------- RECENT TRANSACTIONS ----------------

    def create_recent_transactions(self):
        section = QGroupBox("Recent Transactions")
        inner = QVBoxLayout(section)

        headings = ["Date", "Type", "Category", "Amount", "Description"]
        widths = [100, 85, 130, 110, 250]

        self.recent_table = QTableWidget(0, len(headings))
        self.recent_table.setHorizontalHeaderLabels(headings)
        self.recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        for i, width in enumerate(widths):
            self.recent_table.setColumnWidth(i, width)
        self.recent_table.setMinimumHeight(130)
        self.recent_table.setMaximumHeight(190)

        inner.addWidget(self.recent_table)
        return section

    def update_recent_transactions(self, transactions):
        self.recent_table.setRowCount(0)

        recent = sorted(
            transactions,
            key=lambda transaction: (transaction["date"], transaction["id"]),
            reverse=True,
        )[:10]

        for transaction in recent:
            values = (
                transaction["date"],
                transaction["type"].title(),
                transaction["category"],
                f"${float(transaction['amount']):,.2f}",
                transaction.get("description", ""),
            )
            row = self.recent_table.rowCount()
            self.recent_table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.recent_table.setItem(row, column, item)

    # ---------------- REFRESH DASHBOARD ----------------

    def refresh_dashboard(self, *_args):
        month = self.month_edit.date().toString("yyyy-MM")
        parsed_month = date.fromisoformat(month + "-01")

        try:
            transactions = database.get_transactions({
                "start_date": parsed_month.strftime("%Y-%m-01"),
                "end_date": parsed_month.strftime("%Y-%m-31"),
            })

            summary = finance_logic.calculate_monthly_summary(transactions)

            # Update the three summary cards.
            self.income_label.setText(f"${summary['income']:,.2f}")
            self.expenses_label.setText(f"${summary['expenses']:,.2f}")
            self.balance_label.setText(f"${summary['balance']:,.2f}")

            # Update the charts.
            spending = finance_logic.calculate_category_spending(transactions)
            self.update_expense_chart(spending)
            self.update_comparison_chart(summary["income"], summary["expenses"])

            # Update recent transactions.
            self.update_recent_transactions(transactions)

        except Exception as error:
            QMessageBox.critical(
                self, "Dashboard Error",
                f"Could not load dashboard data:\n{error}",
            )


def create_dashboard(parent=None):
    return DashboardScreen(parent)
