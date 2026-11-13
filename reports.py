"""
Reports screen - PySide6 version of the original Tkinter reports.py.

Entry point is unchanged:  create_reports_screen(parent=None)
It still uses your existing `database` and `finance_logic` modules.
"""

import csv

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QDateEdit, QFileDialog, QGridLayout, QGroupBox,
    QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

import database
import finance_logic


class ReportsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Financial Reports")
        self.report_data = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.create_controls())
        layout.addWidget(self.create_summary())
        layout.addWidget(self.create_report_table(), 1)

    # ---------------- CONTROLS ----------------

    @staticmethod
    def make_date_edit(qdate):
        edit = QDateEdit(qdate)
        edit.setDisplayFormat("yyyy-MM-dd")
        edit.setCalendarPopup(True)
        return edit

    def create_controls(self):
        group = QGroupBox("Generate Financial Report")
        grid = QGridLayout(group)

        today = QDate.currentDate()

        grid.addWidget(QLabel("Start Date (YYYY-MM-DD):"), 0, 0)
        self.start_date_edit = self.make_date_edit(
            QDate(today.year(), today.month(), 1)
        )
        grid.addWidget(self.start_date_edit, 0, 1)

        grid.addWidget(QLabel("End Date (YYYY-MM-DD):"), 0, 2)
        self.end_date_edit = self.make_date_edit(today)
        grid.addWidget(self.end_date_edit, 0, 3)

        for column, (text, slot) in enumerate([
            ("Generate Report", self.generate_report),
            ("Export CSV", self.export_report_csv),
            ("Clear Report", self.clear_report),
        ]):
            button = QPushButton(text)
            button.clicked.connect(slot)
            grid.addWidget(button, 1, column)

        grid.setColumnStretch(4, 1)
        return group

    # ---------------- SUMMARY ----------------

    def create_summary(self):
        group = QGroupBox("Financial Summary")
        inner = QVBoxLayout(group)

        font = QFont()
        font.setPointSize(11)
        font.setBold(True)

        self.income_label = QLabel("Total Income: $0.00")
        self.expenses_label = QLabel("Total Expenses: $0.00")
        self.balance_label = QLabel("Balance: $0.00")

        for label in (self.income_label, self.expenses_label, self.balance_label):
            label.setFont(font)
            inner.addWidget(label)

        return group

    # ---------------- TABLE ----------------

    def create_report_table(self):
        group = QGroupBox("Transaction Details")
        inner = QVBoxLayout(group)

        headings = ["Date", "Type", "Category", "Amount", "Description"]
        widths = [110, 100, 150, 120, 280]

        self.table = QTableWidget(0, len(headings))
        self.table.setHorizontalHeaderLabels(headings)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for i, width in enumerate(widths):
            self.table.setColumnWidth(i, width)

        inner.addWidget(self.table)
        return group

    # ---------------- REPORT ----------------

    def start_text(self):
        return self.start_date_edit.date().toString("yyyy-MM-dd")

    def end_text(self):
        return self.end_date_edit.date().toString("yyyy-MM-dd")

    def get_date_range(self):
        if self.start_date_edit.date() > self.end_date_edit.date():
            QMessageBox.critical(
                self, "Invalid Date Range",
                "The start date cannot be after the end date.",
            )
            return None

        return self.start_text(), self.end_text()

    def generate_report(self):
        date_range = self.get_date_range()
        if date_range is None:
            return

        start_date, end_date = date_range

        try:
            self.report_data = database.get_transactions({
                "start_date": start_date,
                "end_date": end_date,
            })

            summary = finance_logic.calculate_monthly_summary(self.report_data)

            self.income_label.setText(
                f"Total Income: ${summary['income']:,.2f}")
            self.expenses_label.setText(
                f"Total Expenses: ${summary['expenses']:,.2f}")
            self.balance_label.setText(
                f"Balance: ${summary['balance']:,.2f}")

            self.display_transactions()

            if not self.report_data:
                QMessageBox.information(
                    self, "Report Generated",
                    "No transactions were found for this date range.",
                )

        except Exception as error:
            QMessageBox.critical(self, "Report Error", str(error))

    def display_transactions(self):
        self.table.setRowCount(0)

        for transaction in self.report_data:
            values = (
                transaction["date"],
                transaction["type"].title(),
                transaction["category"],
                f"${float(transaction['amount']):,.2f}",
                transaction.get("description", ""),
            )

            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    # ---------------- EXPORT ----------------

    def export_report_csv(self):
        if not self.report_data:
            QMessageBox.warning(self, "No Report",
                                "Generate a report before exporting.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Financial Report", "financial_report.csv",
            "CSV files (*.csv)",
        )
        if not filepath:
            return

        try:
            summary = finance_logic.calculate_monthly_summary(self.report_data)

            with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)

                writer.writerow(["Personal Finance Report"])
                writer.writerow(["Start Date", self.start_text()])
                writer.writerow(["End Date", self.end_text()])
                writer.writerow([])
                writer.writerow(["Total Income", summary["income"]])
                writer.writerow(["Total Expenses", summary["expenses"]])
                writer.writerow(["Balance", summary["balance"]])
                writer.writerow([])
                writer.writerow(["Date", "Type", "Category", "Amount",
                                 "Description"])

                for transaction in self.report_data:
                    writer.writerow([
                        transaction["date"],
                        transaction["type"],
                        transaction["category"],
                        transaction["amount"],
                        transaction.get("description", ""),
                    ])

            QMessageBox.information(self, "Export Successful",
                                    f"Report saved to:\n{filepath}")

        except OSError as error:
            QMessageBox.critical(self, "Export Error",
                                 f"Could not save the report:\n{error}")

    def clear_report(self):
        self.report_data = []
        self.table.setRowCount(0)
        self.income_label.setText("Total Income: $0.00")
        self.expenses_label.setText("Total Expenses: $0.00")
        self.balance_label.setText("Balance: $0.00")


def create_reports_screen(parent=None):
    return ReportsScreen(parent)
