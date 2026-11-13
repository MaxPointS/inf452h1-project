"""
Login dialog.

  * First run (no accounts yet): shows "Create your first account".
  * Afterwards: shows the login form, with a button to create another account.
  * Five wrong attempts close the dialog (the program then exits).

Use:   user = LoginDialog.ask()      # {"id": .., "username": ..}, or None if
                                     # cancelled / locked out
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)

import auth

MAX_ATTEMPTS = 5


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - Personal Finance Management System")
        self.setModal(True)
        self.setFixedWidth(400)

        self.user = None                # set when login / registration succeeds
        self.failed_attempts = 0
        self.register_mode = not auth.has_users()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("Personal Finance\nManagement System")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.heading = QLabel()
        self.heading.setAlignment(Qt.AlignCenter)
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)

        form = QFormLayout()
        form.setVerticalSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username")
        form.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Password")
        form.addRow("Password:", self.password_edit)

        self.confirm_label = QLabel("Confirm:")
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit.setPlaceholderText("Repeat password")
        form.addRow(self.confirm_label, self.confirm_edit)

        layout.addLayout(form)

        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password)
        layout.addWidget(self.show_password)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c62828;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        self.submit_button = QPushButton()
        self.submit_button.setDefault(True)          # Enter key submits
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        self.switch_button = QPushButton()
        self.switch_button.setFlat(True)
        self.switch_button.clicked.connect(self.toggle_mode)
        layout.addWidget(self.switch_button)

        self.update_mode()
        self.username_edit.setFocus()

    # ---------------- helpers ----------------

    def toggle_password(self, visible):
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        self.password_edit.setEchoMode(mode)
        self.confirm_edit.setEchoMode(mode)

    def show_error(self, message):
        self.error_label.setText(message)

    def update_mode(self):
        first_run = not auth.has_users()

        if self.register_mode:
            self.heading.setText(
                "Create your first account to get started."
                if first_run else "Create a new account."
            )
            self.submit_button.setText("Create account")
            self.switch_button.setText("Back to login")
        else:
            self.heading.setText("Sign in to continue.")
            self.submit_button.setText("Log in")
            self.switch_button.setText("Create a new account")

        self.confirm_label.setVisible(self.register_mode)
        self.confirm_edit.setVisible(self.register_mode)
        # Nothing to go back to until the first account exists.
        self.switch_button.setVisible(not (self.register_mode and first_run))

        self.show_error("")
        self.password_edit.clear()
        self.confirm_edit.clear()
        self.adjustSize()

    def toggle_mode(self):
        self.register_mode = not self.register_mode
        self.update_mode()
        self.username_edit.setFocus()

    # ---------------- actions ----------------

    def submit(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if self.register_mode:
            self.submit_register(username, password)
        else:
            self.submit_login(username, password)

    def submit_register(self, username, password):
        if password != self.confirm_edit.text():
            self.show_error("Passwords do not match.")
            return

        user, message = auth.register(username, password)
        if user is None:
            self.show_error(message)
            return

        self.user = user
        self.accept()

    def submit_login(self, username, password):
        user = auth.authenticate(username, password)

        if user:
            self.user = user
            self.accept()
            return

        self.failed_attempts += 1
        remaining = MAX_ATTEMPTS - self.failed_attempts

        if remaining <= 0:
            self.reject()
            return

        self.password_edit.clear()
        self.password_edit.setFocus()
        self.show_error(
            f"Incorrect username or password. "
            f"{remaining} attempt{'s' if remaining != 1 else ''} left."
        )

    # ---------------- entry point ----------------

    @staticmethod
    def ask():
        """Show the dialog. Returns the user dict, or None if cancelled."""
        dialog = LoginDialog()
        dialog.exec()
        return dialog.user
