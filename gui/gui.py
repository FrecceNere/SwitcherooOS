#!/usr/bin/env python3

from PySide6.QtWidgets import QApplication, QMainWindow
from gui.windows_ui import Ui_MainWindow

class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.stackedWidget.setCurrentIndex(0)

        self.pushButton.clicked.connect(self.on_pushButton_clicked)

    def on_pushButton_clicked(self):
        sw = self.stackedWidget
        next_idx = (sw.currentIndex() + 1) % sw.count()
        sw.setCurrentIndex(next_idx)
        #self.stackedWidget.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication([])
    win = MainApp()
    win.show()
    app.exec()
