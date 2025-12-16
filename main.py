import sys
from gui import MainWindow, resource_path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("bili.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
