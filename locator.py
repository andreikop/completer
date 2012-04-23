from PyQt4.QtCore import pyqtSignal, QAbstractItemModel, QModelIndex, QSize, Qt
from PyQt4.QtGui import QApplication, QFontMetrics, QPalette, QSizePolicy, QStyle, \
                        QStyle, QStyleOptionFrameV2, \
                        QTextCursor, QTextEdit, QTextOption, QTreeView, QVBoxLayout, QWidget

import os

from pyparsing import Optional, Or, ParseException, StringEnd, White


from htmldelegate import HTMLDelegate

class AbstractCommand:
    @staticmethod
    def signature():
        raise NotImplemented()
    
    @staticmethod
    def description():
        raise NotImplemented()

    @staticmethod
    def pattern():
        raise NotImplemented()
    
    def completer(self, text, pos):
        return None

    @staticmethod
    def isAvailable():
        return True

    def isReadyToExecute(self):
        return True

    def execute(self):
        raise NotImplemented()


class AbstractCompleter:
    def rowCount(self):
        raise NotImplemented()
    
    def columnCount(self):
        return 1
    
    def text(self, row, column):
        raise NotImplemented()
    
    def icon(self, row, column):
        return None
    
    def inline(self):
        return None
    
    def inlineForRow(self, row):
        return None


class _HelpCompleter(AbstractCompleter):
    def __init__(self, commands):
        self._commands = commands
    
    def rowCount(self):
        return len(self._commands)
    
    def columnCount(self):
        return 2
    
    def text(self, row, column):
        if column == 0:
            return self._commands[row].signature()
        else:
            return self._commands[row].description()


class _CompleterModel(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.completer = None

    def index(self, row, column, parent):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def rowCount(self, index):
        if index.isValid():
            return 0
        if self.completer is None:
            return 0
        
        return self.completer.rowCount()
    
    def columnCount(self, index):
        if self.completer is None:
            return 0
        return self.completer.columnCount()
    
    def data(self, index, role):
        if self.completer is None:
            return None
        if role == Qt.DisplayRole:
            return self.completer.text(index.row(), index.column())
        elif role == Qt.DecorationRole:
            return self.completer.icon(index.row(), index.column())
        return None
    
    def setCompleter(self, completer):
        self.completer = completer
        self.modelReset.emit()


class _CompletableLineEdit(QTextEdit):
    updateCompletion = pyqtSignal()
    enterPressed = pyqtSignal()
    historyPrevious = pyqtSignal()
    historyNext = pyqtSignal()
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
                self.updateCompletion.emit()
            return True
        else:
            return QTextEdit.event(self, event)
    
    def keyPressEvent(self, event):
        self._clearInlineCompletion()
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.enterPressed.emit()
        elif event.key() == Qt.Key_Up:
            self.historyPrevious.emit()
        elif event.key() == Qt.Key_Down:
            self.historyNext.emit()
        else:
            QTextEdit.keyPressEvent(self, event)
        self.updateCompletion.emit()
    
    def mousePressEvent(self, event):
        self._clearInlineCompletion()
        QTextEdit.mousePressEvent(self, event)
        if self.textCursor().atEnd():
            self.updateCompletion.emit()

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
    
    def setPlainText(self, text):
        self.setInlineCompletion('')
        QTextEdit.setPlainText(self, text)
        self.moveCursor(QTextCursor.End)
    
    def insertPlainText(self, text):
        self._clearInlineCompletion()
        QTextEdit.insertPlainText(self, text)


class Locator(QWidget):
    def __init__(self, *args):
        QWidget.__init__(self, *args)
        
        self._commandClasses = []
        self._history = ['']
        self._historyIndex = 0
        self._incompleteCommand = None
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(1)
        
        self._table = QTreeView(self)
        self._model = _CompleterModel()
        self._table.setModel(self._model)
        self._table.setItemDelegate(HTMLDelegate())
        self._table.setRootIsDecorated(False)
        self._table.setHeaderHidden(True)
        self._table.clicked.connect(self._onItemClicked)
        self.layout().addWidget(self._table)
        
        self._edit = _CompletableLineEdit(self)
        self.layout().addWidget(self._edit)
        self._edit.updateCompletion.connect(self._updateCompletion)
        self._edit.enterPressed.connect(self._onEnterPressed)
        self._edit.historyPrevious.connect(self._onHistoryPrevious)
        self._edit.historyNext.connect(self._onHistoryNext)
        self.setFocusProxy(self._edit)

        self._edit.setFocus()
        self._updateCompletion()

    def _onItemClicked(self, index):
        inlineForRow = self._model.completer.inlineForRow(index.row())
        if inlineForRow is not None:
            self._edit.insertPlainText(inlineForRow)
            self._updateCompletion()
            self._edit.setFocus()
            self._onEnterPressed()

    def _updateCompletion(self):
        text = self._edit.toPlainText()
        completer = None
        
        command = self._parseCommand(text)
        if command is not None:
            completer = command.completer(self._edit.toPlainText(), self._edit.textCursor().position())

            if completer is not None:
                inline = completer.inline()
                if inline:
                    self._edit.setInlineCompletion(inline)
            else:
                completer = _HelpCompleter([command])
        else:
            completer = _HelpCompleter(self._availableCommands())

        self._model.setCompleter(completer)
        self._table.resizeColumnToContents(0)
        self._table.setColumnWidth(0, self._table.columnWidth(0) + 20)  # 20 px spacing between columns
    
    def _onEnterPressed(self):
        text = self._edit.toPlainText().strip()
        command = self._parseCommand(text)
        if command is not None and command.isReadyToExecute():
            command.execute()
            self._history[-1] = text
            if len(self._history) > 1 and \
               self._history[-1].strip() == self._history[-2].strip():
                   self._history = self._history[:-1]  # if the last command repeats, remove duplicate
            self._history.append('')  # new edited command
            self._historyIndex = len(self._history) - 1
            self._edit.clear()
            self._updateCompletion()
    
    def _onHistoryPrevious(self):
        if self._historyIndex == len(self._history) - 1:  # save edited command
            self._history[self._historyIndex] = self._edit.toPlainText()
        
        if self._historyIndex > 0:
            self._historyIndex -= 1
            self._edit.setPlainText(self._history[self._historyIndex])
    
    def _onHistoryNext(self):
        if self._historyIndex < len(self._history) - 1:
            self._historyIndex += 1
            self._edit.setPlainText(self._history[self._historyIndex])
    
    def addCommandClass(self, commandClass):
        self._commandClasses.append(commandClass)
    
    def removeCommandClass(self, commandClass):
        self._commandClasses.remove(commandClass)
    
    def _availableCommands(self):
        return [cmd for cmd in self._commandClasses if cmd.isAvailable()]

    def _parseCommand(self, text):
        optWs = Optional(White()).suppress()
        pattern = optWs + Or([cmd.pattern() for cmd in self._availableCommands()]) + optWs + StringEnd()
        try:
            res = pattern.parseString(text)
            return res[0]
        except ParseException:
            return None

    def show(self):
        self._updateCompletion()
        QWidget.show(self)
