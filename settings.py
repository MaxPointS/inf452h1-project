"""
Settings screen - PySide6 version of the original Tkinter settings.py.

Entry point is unchanged:  create_settings_screen(parent=None)
It still uses `database.get_setting()` / `database.save_setting()`.

Changes from the Tkinter version
  * Theme (Light / Dark) is now really applied, not just saved.
  * Font size is applied to the whole application (QApplication font).
  * apply_saved_settings() is called by main_mdi.py at start-up so your
    saved theme and font size are used every time the program opens.
  * Language and currency are still stored only (nothing else in the
    application reads them yet), same as before.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import database

DEFAULTS = {
    "theme": "Light",
    "font_size": "Medium",
    "language": "English",
    "currency": "CAD",
}

FONT_SIZES = {"Small": 9, "Medium": 10, "Large": 13}


# --------------------------------------------------------------------------- #
# Application-wide appearance (also used by main_mdi.py at start-up)
# --------------------------------------------------------------------------- #
def apply_theme(theme):
    app = QApplication.instance()
    if app is None:
        return

    app.setStyle("Fusion")

    if theme == "Dark":
        palette = QPalette()
        light = QColor(230, 230, 230)
        palette.setColor(QPalette.Window, QColor(45, 45, 48))
        palette.setColor(QPalette.WindowText, light)
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ToolTipText, light)
        palette.setColor(QPalette.Text, light)
        palette.setColor(QPalette.Button, QColor(60, 60, 64))
        palette.setColor(QPalette.ButtonText, light)
        palette.setColor(QPalette.BrightText, QColor("red"))
        palette.setColor(QPalette.Link, QColor(80, 160, 255))
        palette.setColor(QPalette.Highlight, QColor(21, 101, 192))
        palette.setColor(QPalette.HighlightedText, QColor("white"))
        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            palette.setColor(QPalette.Disabled, role, QColor(120, 120, 120))
        app.setPalette(palette)
    else:
        app.setPalette(app.style().standardPalette())


def apply_font_size(size):
    app = QApplication.instance()
    if app is None:
        return

    font = app.font()
    font.setPointSize(FONT_SIZES.get(size, FONT_SIZES["Medium"]))
    app.setFont(font)


def apply_saved_settings():
    """Apply the theme and font size stored in the database (if any)."""
    theme = database.get_setting("theme")
    font_size = database.get_setting("font_size")

    if theme:
        apply_theme(theme)
    if font_size:
        apply_font_size(font_size)


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")

        self.create_settings_form()
        self.load_settings()

    def create_settings_form(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Application Settings")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form_box = QGroupBox("Preferences")
        form = QFormLayout(form_box)
        form.setVerticalSpacing(14)

        self.theme_box = QComboBox()
        self.theme_box.addItems(["Light", "Dark"])
        form.addRow("Theme:", self.theme_box)

        self.font_size_box = QComboBox()
        self.font_size_box.addItems(["Small", "Medium", "Large"])
        form.addRow("Font Size:", self.font_size_box)

        self.language_box = QComboBox()
        self.language_box.addItems(["English", "Arabic"])
        form.addRow("Language:", self.language_box)

        self.currency_box = QComboBox()
        self.currency_box.addItems(["CAD", "USD", "EUR", "EGP"])
        form.addRow("Currency:", self.currency_box)

        layout.addWidget(form_box)

        # Buttons
        buttons = QHBoxLayout()
        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings)
        buttons.addWidget(save)

        reset = QPushButton("Reset Settings")
        reset.clicked.connect(self.reset_settings)
        buttons.addWidget(reset)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.status_label = QLabel(
            "Changes are applied when supported by the application."
        )
        layout.addWidget(self.status_label)
        layout.addStretch()

    # ---------------- LOAD / SAVE ----------------

    def load_settings(self):
        try:
            self.theme_box.setCurrentText(
                database.get_setting("theme") or DEFAULTS["theme"])
            self.font_size_box.setCurrentText(
                database.get_setting("font_size") or DEFAULTS["font_size"])
            self.language_box.setCurrentText(
                database.get_setting("language") or DEFAULTS["language"])
            self.currency_box.setCurrentText(
                database.get_setting("currency") or DEFAULTS["currency"])

        except Exception as error:
            QMessageBox.critical(self, "Settings Error",
                                 f"Could not load settings:\n{error}")

    def get_settings(self):
        return {
            "theme": self.theme_box.currentText(),
            "font_size": self.font_size_box.currentText(),
            "language": self.language_box.currentText(),
            "currency": self.currency_box.currentText(),
        }

    def save_settings(self):
        settings = self.get_settings()

        try:
            for key, value in settings.items():
                database.save_setting(key, value)

            apply_theme(settings["theme"])
            apply_font_size(settings["font_size"])

            self.status_label.setText("Settings saved successfully.")
            QMessageBox.information(self, "Settings Saved",
                                    "Your preferences have been saved.")

        except Exception as error:
            QMessageBox.critical(self, "Settings Error",
                                 f"Could not save settings:\n{error}")

    def reset_settings(self):
        confirm = QMessageBox.question(
            self, "Reset Settings",
            "Restore the default application settings?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            for key, value in DEFAULTS.items():
                database.save_setting(key, value)

            self.theme_box.setCurrentText(DEFAULTS["theme"])
            self.font_size_box.setCurrentText(DEFAULTS["font_size"])
            self.language_box.setCurrentText(DEFAULTS["language"])
            self.currency_box.setCurrentText(DEFAULTS["currency"])

            apply_theme(DEFAULTS["theme"])
            apply_font_size(DEFAULTS["font_size"])

            self.status_label.setText("Default settings restored.")
            QMessageBox.information(self, "Settings Reset",
                                    "Default preferences have been restored.")

        except Exception as error:
            QMessageBox.critical(self, "Settings Error",
                                 f"Could not reset settings:\n{error}")


def create_settings_screen(parent=None):
    return SettingsScreen(parent)
