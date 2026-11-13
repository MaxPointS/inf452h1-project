"""
Personal Finance Management System - MDI main window (PySide6)

Each screen lives in its own file and is opened as a child window from the
menu bar.  To add another screen later (e.g. transactions.py):

    1. from transactions import create_transactions_screen
    2. add one line to SCREENS below

Files needed in the same folder:
    main_mdi.py   dashboard.py   transactions.py   budgets.py
    reports.py    settings.py    login.py          auth.py
    database.py   finance_logic.py

Install:  pip install PySide6 matplotlib
Run:      python main_mdi.py
"""

import sys

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMdiArea, QMdiSubWindow,
    QLabel, QMessageBox, QWidget,
)

from dashboard import create_dashboard
from transactions import create_transactions_screen
from budgets import create_budgets_screen
from reports import create_reports_screen
from settings import create_settings_screen, apply_saved_settings
from login import LoginDialog
import database

# (menu title, factory function, shortcut, default window size)
SCREENS = [
    ("Dashboard", create_dashboard, "Ctrl+1", (920, 660)),
    ("Transactions", create_transactions_screen, "Ctrl+2", (900, 620)),
    ("Budgets", create_budgets_screen, "Ctrl+3", (860, 560)),
    ("Reports", create_reports_screen, "Ctrl+4", (880, 600)),
    ("Settings", create_settings_screen, "Ctrl+5", (520, 440)),
]


# Optional default background, e.g. "background.jpg" (next to this file).
# Leave empty to use the image chosen via  Window -> Set background image...
BACKGROUND_IMAGE = ""


class ImageMdiArea(QMdiArea):
    """QMdiArea that paints a picture scaled to fill the whole area."""

    def __init__(self, image_path=""):
        super().__init__()
        self.pixmap = QPixmap()
        self.setBackground(QColor("#2b2f3a"))      # fallback colour
        if image_path:
            self.set_image(image_path)

    def set_image(self, image_path):
        """Returns True if the image loaded, False otherwise."""
        self.pixmap = QPixmap(image_path) if image_path else QPixmap()
        self.viewport().update()
        return not self.pixmap.isNull()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        area = self.viewport().rect()
        painter.fillRect(area, self.background())

        if not self.pixmap.isNull():
            # Cover the whole area, keep aspect ratio, crop the overflow.
            scaled = self.pixmap.scaled(
                area.size(), Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (scaled.width() - area.width()) // 2
            y = (scaled.height() - area.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, area.width(), area.height())

        painter.end()


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, username=""):
        super().__init__()
        self.username = username
        self._logging_out = False
        self.setWindowTitle("Personal Finance Management System")
        self.resize(1200, 780)

        self.settings = QSettings("PersonalFinance", "MDI")
        self.mdi = ImageMdiArea(
            BACKGROUND_IMAGE or self.settings.value("background", "")
        )
        self.setCentralWidget(self.mdi)
        self.statusBar().showMessage("Ready")
        if username:
            self.statusBar().addPermanentWidget(
                QLabel(f"Signed in as {username}   ")
            )

        self.open_windows = {}      # screen title -> QMdiSubWindow
        self.build_menus()

        # Open the dashboard on start-up.
        self.open_screen(*SCREENS[0])

    # ---------------- MENUS ----------------

    def build_menus(self):
        bar = self.menuBar()

        # File
        file_menu = bar.addMenu("&File")

        logout_action = QAction("&Log out", self)
        logout_action.setShortcut(QKeySequence("Ctrl+L"))
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Screens: one menu item per entry in SCREENS
        screens_menu = bar.addMenu("&Screens")
        for title, factory, shortcut, size in SCREENS:
            action = QAction(title, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(
                lambda _checked=False, t=title, f=factory, s=shortcut, z=size:
                    self.open_screen(t, f, s, z)
            )
            screens_menu.addAction(action)

        # Window
        window_menu = bar.addMenu("&Window")

        cascade = QAction("Cascade", self)
        cascade.triggered.connect(self.mdi.cascadeSubWindows)
        window_menu.addAction(cascade)

        tile = QAction("Tile", self)
        tile.triggered.connect(self.mdi.tileSubWindows)
        window_menu.addAction(tile)

        tabbed = QAction("Tabbed view", self, checkable=True)
        tabbed.toggled.connect(self.set_tabbed)
        window_menu.addAction(tabbed)

        window_menu.addSeparator()
        set_bg = QAction("Set background image...", self)
        set_bg.triggered.connect(self.choose_background)
        window_menu.addAction(set_bg)

        clear_bg = QAction("Clear background image", self)
        clear_bg.triggered.connect(self.clear_background)
        window_menu.addAction(clear_bg)

        window_menu.addSeparator()
        close_all = QAction("Close all", self)
        close_all.triggered.connect(self.mdi.closeAllSubWindows)
        window_menu.addAction(close_all)

    def logout(self):
        """Close this window and tell main() to show the login dialog again."""
        self._logging_out = True
        database.set_current_user(None)
        self.close()
        self.logout_requested.emit()

    def closeEvent(self, event):
        event.accept()
        if not self._logging_out:
            QApplication.quit()          # normal close = exit the program

    def choose_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose background image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        if self.mdi.set_image(path):
            self.settings.setValue("background", path)   # remembered next launch
        else:
            QMessageBox.warning(self, "Background",
                                "That file could not be loaded as an image.")

    def clear_background(self):
        self.mdi.set_image("")
        self.settings.setValue("background", "")

    def set_tabbed(self, on):
        if on:
            self.mdi.setViewMode(QMdiArea.TabbedView)
            self.mdi.setTabsClosable(True)
            self.mdi.setTabsMovable(True)
        else:
            self.mdi.setViewMode(QMdiArea.SubWindowView)

    # ---------------- CHILD WINDOWS ----------------

    def open_screen(self, title, factory, _shortcut=None, size=(900, 600)):
        """Open the screen in a child window, or focus it if already open."""
        existing = self.open_windows.get(title)
        if existing is not None:
            existing.showNormal()
            self.mdi.setActiveSubWindow(existing)
            return

        try:
            screen = factory()
        except Exception as error:
            QMessageBox.critical(
                self, "Could not open screen", f"{title}:\n{error}"
            )
            return

        # Accept a QWidget, or a wrapper object that exposes one as .frame / .widget
        widget = screen if isinstance(screen, QWidget) else (
            getattr(screen, "frame", None) or getattr(screen, "widget", None)
        )
        if not isinstance(widget, QWidget):
            QMessageBox.critical(
                self, "Could not open screen",
                f"{title}: the factory returned {type(screen).__module__}."
                f"{type(screen).__name__}, which is not a QWidget.\n\n"
                "Make sure dashboard.py / budgets.py are the PySide6 versions "
                "(class must inherit QWidget), not the old Tkinter files."
            )
            return

        sub = QMdiSubWindow()
        sub._screen = screen          # keep wrapper objects alive
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.setAttribute(Qt.WA_DeleteOnClose)
        sub.resize(*size)
        sub.destroyed.connect(lambda *_a, t=title: self.open_windows.pop(t, None))

        self.mdi.addSubWindow(sub)
        sub.show()
        self.open_windows[title] = sub
        self.statusBar().showMessage(f"Opened {title}", 3000)


def main():
    app = QApplication(sys.argv)

    # Create the tables (or upgrade an old single-user finance.db).
    try:
        database.initialize_db()
    except Exception as error:
        QMessageBox.critical(
            None, "Database error", f"Could not open the database:\n{error}"
        )
        return

    # Use the theme / font size saved in the Settings screen.
    try:
        apply_saved_settings()
    except Exception as error:
        print(f"Could not apply saved settings: {error}")

    # We decide when to quit (see MainWindow.closeEvent), so that logging out
    # does not end the program while the login dialog is about to appear.
    app.setQuitOnLastWindowClosed(False)
    state = {}                           # keeps a reference to the open window

    def show_login():
        user = LoginDialog.ask()
        if user is None:                 # cancelled or too many wrong attempts
            app.quit()
            return

        database.set_current_user(user["id"])   # all data is now this user's
        window = MainWindow(user["username"])
        window.logout_requested.connect(lambda: QTimer.singleShot(0, show_login))
        state["window"] = window
        window.show()

    QTimer.singleShot(0, show_login)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
