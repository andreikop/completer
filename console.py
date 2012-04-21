#!/usr/bin/env python

import sip
sip.setapi('QString', 2)

from PyQt4.QtCore import pyqtSignal, QSize, Qt
from PyQt4.QtGui import QApplication, QFontMetrics, QPalette, QSizePolicy, QStyle, \
                        QStyle, QStyleOptionFrameV2, \
                        QTextCursor, QTextEdit, QTextOption, QListView, QVBoxLayout, QWidget

import os
import sys

from htmldelegate import HTMLDelegate
import commands

from PyQt4.QtCore import QAbstractItemModel, QModelIndex

class HelpCompleter:
    def __init__(self, commands):
        self._commands = commands
    
    def rowCount(self):
        return len(self._commands)
    
    def item(self, row):
        return self._commands[row].description
    
    def inline(self):
        return None

class ShowDescriptionCompleter:
    def __init__(self, text):
        self._text = text
    
    def rowCount(self):
        return 1
    
    def item(self, row):
        return self._text
    
    def inline(self):
        return None


class ListModel(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self._completer = None

    def index(self, row, column, parent):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def rowCount(self, index):
        if index.isValid():
            return 0
        if self._completer is None:
            return 0
        
        return self._completer.rowCount()
    
    def columnCount(self, index):
        return 1
    
    def data(self, index, role):
        if self._completer is None:
            return None
        if role == Qt.DisplayRole:
            return self._completer.item(index.row())
        return None
    
    def flags(self, index):
        retVal = QAbstractItemModel.flags(self, index)
        retVal &= ~Qt.ItemIsSelectable  # clear flag
        return retVal
    
    def setCompleter(self, completer):
        self._completer = completer
        self.modelReset.emit()


class CompletableLineEdit(QTextEdit):
    tryToComplete = pyqtSignal()
    enterPressed = pyqtSignal()
    def __init__(self, *args):
        QTextEdit.__init__(self, *args)
        self.setTabChangesFocus(True)
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.sizeHint().height())
        self._inlineCompletion = None
        
    def sizeHint(self):
        fm = QFontMetrics(self.font())
        h = max(fm.height(), 14) + 4
        w = fm.width('x') * 17 + 4
        opt = QStyleOptionFrameV2()
        opt.initFrom(self);
        return self.style().sizeFromContents(QStyle.CT_LineEdit,
                                             opt,
                                             QSize(w, h).expandedTo(QApplication.globalStrut()),
                                             self)

    def event(self, event):
        if event.type() == event.KeyPress and \
           event.key() == Qt.Key_Tab:
            if self._inlineCompletion is not None:
                color = self.palette().color(QPalette.Base).name()
                self.insertHtml('<font style="background-color: %s">%s</font>' % (color, self._inlineCompletion))
                self._clearInlineCompletion()
                self.tryToComplete.emit()
            return True
        else:
            return QTextEdit.event(self, event)
    
    def keyPressEvent(self, event):
        self._clearInlineCompletion()
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.enterPressed.emit()
        else:
            QTextEdit.keyPressEvent(self, event)
        self.tryToComplete.emit()
    
    def mousePressEvent(self, event):
        self._clearInlineCompletion()
        QTextEdit.mousePressEvent(self, event)
        if self.textCursor().atEnd():
            self.tryToComplete.emit()

    def _clearInlineCompletion(self):
        if self._inlineCompletion is not None:
            cursor = self.textCursor()
            for c in self._inlineCompletion:
                cursor.deleteChar()
            self._inlineCompletion = None
    
    def setInlineCompletion(self, text):
        self._inlineCompletion = text
        cursor = self.textCursor()
        pos = cursor.position()
        color = self.palette().color(QPalette.Highlight).name()
        cursor.insertHtml('<font style="background-color: %s">%s</font>' % (color, text))
        cursor.setPosition(pos)
        self.setTextCursor(cursor)
    
    def text(self):
        return self.toPlainText()

class CommandConsole(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(1)
        
        self._table = QListView(self)
        self._model = ListModel()
        self._table.setModel(self._model)
        self._table.setItemDelegate(HTMLDelegate())
        self.layout().addWidget(self._table)
        
        self._edit = CompletableLineEdit(self)
        self.layout().addWidget(self._edit)
        self._edit.tryToComplete.connect(self._tryToComplete)
        self._edit.enterPressed.connect(self._enterPressed)
        self.setFocusProxy(self._edit)

        self._edit.setFocus()
        self._tryToComplete()

    def _tryToComplete(self):
        text = self._edit.toPlainText()
        completer = None
        
        command = commands.parseCommand(text)
        if command is not None:
            completer = command.completion(self._edit.textCursor().position())

            if completer is not None:
                inline = completer.inline()
                if inline:
                    self._edit.setInlineCompletion(inline)
            else:
                completer = ShowDescriptionCompleter(command.description)
        else:
            completer = HelpCompleter(commands.commands)

        self._model.setCompleter(completer)
    
    def _enterPressed(self):
        text = self._edit.toPlainText()
        command = commands.parseCommand(text)
        if command is not None and command.readyToExecute():
            command.execute()

def main():
    app = QApplication(sys.argv)
    w = CommandConsole()
    w.show()
    return app.exec_()

if __name__ == '__main__':
    main()
