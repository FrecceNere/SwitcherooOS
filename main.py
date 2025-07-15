#!/usr/bin/env python3
import subprocess
import os
import re
import gui.gui
import gui.windows_ui
import gui.image_rc
from gui.gui import MainApp
from PySide6.QtWidgets import QApplication

def is_live():
    out = subprocess.check_output("df ~", shell=True).decode()
    full = out.strip().split("\n")[-1].split()[0]
    fs_device = full.split("/")[-1]  # ex. "loop0", "sda1", "nvme0n1p2"

    parts = subprocess.check_output("cat /proc/partitions", shell=True).decode().split()

    valid = [p for p in parts if re.match(r'(sd.|nvme.*|hd.|mmcblk.)\d*', p)]

    if fs_device not in valid:
        try:
            cg = subprocess.check_output("cat /proc/1/cgroup", shell=True).decode()
            if "container" in cg:
                return False
        except:
            pass
        return True

    return False

if __name__ == "__main__":
    app = QApplication([])

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
