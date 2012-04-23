#!/usr/bin/env python

import sys

import sip
sip.setapi('QString', 2)

from PyQt4.QtGui import QApplication

from locator import Locator
from commands import CommandOpen, CommandGotoLine

def main():
    app = QApplication(sys.argv)
    locator = Locator()
    locator.addCommandClass(CommandOpen)
    locator.addCommandClass(CommandGotoLine)
    locator.show()
    return app.exec_()

if __name__ == '__main__':
    main()

