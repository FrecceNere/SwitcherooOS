#!/usr/bin/env python3

# SwitcherooOS - helps to switch to a linux distro easily
# Copyright (C) 2025  Raffaele
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtWidgets import QApplication, QMainWindow
from gui.windows_ui import Ui_MainWindow

class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.stackedWidget.setCurrentIndex(0)

        self.pushButton.clicked.connect(self.on_pushButton_clicked)
        self.pushButton_2.clicked.connect(self.on_pushButton_2_clicked)
        self.pushButton_3.clicked.connect(self.on_pushButton_3_clicked)

    def on_pushButton_clicked(self):
        sw = self.stackedWidget
        next_idx = (sw.currentIndex() + 1) % sw.count()
        sw.setCurrentIndex(next_idx)
        #self.stackedWidget.setCurrentIndex(1)

    def on_pushButton_2_clicked(self):
        sw = self.stackedWidget
        next_idx = (sw.currentIndex() + 1) % sw.count()
        sw.setCurrentIndex(next_idx)
        #self.stackedWidget.setCurrentIndex(1)

    def on_pushButton_3_clicked(self):
        sw = self.stackedWidget
        next_idx = (sw.currentIndex() + 1) % sw.count()
        sw.setCurrentIndex(next_idx)
        #self.stackedWidget.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication([])
    win = MainApp()
    win.show()
    app.exec()
