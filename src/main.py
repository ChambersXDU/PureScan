from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from controller.document_controller import DocumentController
import sys

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = DocumentController(window)
    window.controller = controller
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()