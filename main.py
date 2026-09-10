import sys
import multiprocessing
import numpy  # <-- FORÇA O CARREGAMENTO ÚNICO AQUI

if __name__ == "__main__":
    # Necessário para o PyInstaller lidar corretamente com bibliotecas que 
    # iniciam subprocessos (como o Numpy/Matplotlib)
    multiprocessing.freeze_support()

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from qfluentwidgets import setTheme, Theme
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    setTheme(Theme.LIGHT)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
