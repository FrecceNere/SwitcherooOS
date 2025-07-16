#!/usr/bin/env python3
import subprocess
import os
import re
import platform
import gui.gui
import gui.windows_ui
import gui.image_rc
from gui.gui import MainApp
from PySide6.QtWidgets import QApplication

def is_live():
    out = subprocess.run("df ~", shell=True, capture_output=True, text=True, check=False)
    fs = out.stdout.strip().split("\n")[-1].split()[0].split("/")[-1]

    parts = subprocess.run("awk '{print $4}' /proc/partitions", shell=True, capture_output=True, text=True)
    devices = parts.stdout.split()

    # Only keep real disk devices (sd*, nvme*, mmcblk*)
    real = [p for p in devices if re.match(r'^(sd\w+|nvme\d+n\d+p?\d*|mmcblk\d+p?\d*)$', p)]
    if fs not in real:
        cg = subprocess.run("cat /proc/1/cgroup", shell=True, capture_output=True, text=True)
        return True # Home not on real disk = live session

    return False # Home on real disk = installed system

if __name__ == "__main__":
    system = platform.system()
    app = QApplication([])

    if system == "Windows":
        win = MainApp()

    elif system == "Linux":
        if is_live():
            # TODO: Show live linux gui
            # DEBUG: print("Live distro")
            pass
        else:
            # TODO: Show installed linux gui
            # DEBUG: win = MainApp()
            # DEBUG: win.show()
            # DEBUG: app.exec()
            # DEBUG: print("Installed distro")
            pass
