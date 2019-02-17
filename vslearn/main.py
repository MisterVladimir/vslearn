# -*- coding: utf-8 -*-
import sys
from qtpy.QtWidgets import QApplication


from vslearn.main_window import WMainWindow


def run():
    app = QApplication(sys.argv)
    with WMainWindow() as mw:
        mw.show()
        app.exec_()


if __name__ == "__main__":
    run()
