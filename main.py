import os
import sys

os.environ["QT_API"] = "PySide6"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qfluentwidgets import setTheme, Theme

from ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    setTheme(Theme.LIGHT)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
