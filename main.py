#!/usr/bin/env python

import sys

import sip
sip.setapi('QString', 2)

from PyQt4.QtGui import QApplication

from locator import Locator
from workspace_commands import CommandGotoLine, CommandOpen, CommandSaveAs

def main():
    app = QApplication(sys.argv)
    locator = Locator()
    locator.addCommandClass(CommandGotoLine)
    locator.addCommandClass(CommandOpen)
    locator.addCommandClass(CommandSaveAs)
    locator.show()
    return app.exec_()

if __name__ == '__main__':
    main()

