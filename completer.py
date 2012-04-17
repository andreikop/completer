#!/usr/bin/env python

import sip
sip.setapi('QString', 2)

from PyQt4.QtCore import pyqtSignal, QSize, Qt
from PyQt4.QtGui import QApplication, QFontMetrics, QPalette, QSizePolicy, QStyle, \
                        QStyle, QStyleOptionFrameV2, \
                        QTextCursor, QTextEdit, QTextOption, QListView, QVBoxLayout, QWidget

import sys

from PyQt4 import QtGui
from PyQt4 import QtCore
class HTMLDelegate(QtGui.QStyledItemDelegate):
    #http://stackoverflow.com/questions/1956542/how-to-make-item-view-render-rich-html-text-in-qt/1956781#1956781
    def paint(self, painter, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)

        style = QtGui.QApplication.style() if options.widget is None else options.widget.style()

        doc = QtGui.QTextDocument()
        doc.setDocumentMargin(1)
        doc.setHtml(options.text)
        #  bad long (multiline) strings processing doc.setTextWidth(options.rect.width())

        options.text = ""
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, options, painter);

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        #if (optionV4.state & QStyle::State_Selected)
            #ctx.palette.setColor(QPalette::Text, optionV4.palette.color(QPalette::Active, QPalette::HighlightedText));

        textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)

        doc = QtGui.QTextDocument()
        doc.setDocumentMargin(1)
        #  bad long (multiline) strings processing doc.setTextWidth(options.rect.width())
        doc.setHtml(options.text)
        return QtCore.QSize(doc.idealWidth(), doc.size().height())


from PyQt4.QtCore import QAbstractItemModel, QModelIndex
from PyQt4.QtGui import qApp, QFileSystemModel

class ListModel(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self._completion = Completion('')  # initial, empty
        self._fsModel = QFileSystemModel()

    def index(self, row, column, parent):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def rowCount(self, index):
        return self._completion.count()
    
    def columnCount(self, index):
        return 2
    
    def data(self, index, role):
        itemType, item = self._completion.item(index.row())
        if role == Qt.DisplayRole:
            if itemType == 'error':
                return self._formatError(item)
            elif itemType == 'currentDir':
                return self._formatCurrentDir(item)
            elif itemType in ('file', 'directory'):
                return self._formatListItem(item)
            else:
                assert False
        elif role == Qt.DecorationRole:
            if itemType == 'error':
                return qApp.style().standardIcon(QStyle.SP_MessageBoxCritical)
            elif itemType == 'currentDir':
                return None
            elif itemType in ('file', 'directory'):
                index = self._fsModel.index(os.path.join(self._completion.path, item))
                return self._fsModel.data(index, role)
            
        return None
    
    def flags(self, index):
        retVal = QAbstractItemModel.flags(self, index)
        itemType, item = self._completion.item(index.row())
        if itemType in ('error', 'currentDir'):
            retVal &= ~Qt.ItemIsSelectable  # clear flag
        return retVal
    
    def setCompletion(self, completion):
        self._completion = completion
        self.modelReset.emit()

    def _formatListItem(self, text):
        typedLen = self._completion.lastTypedSegmentLength()
        return '<b>%s</b>%s' % (text[:typedLen], text[typedLen:])

    def _formatError(self, text):
        return '<i>%s</i>' % text
    
    def _formatCurrentDir(self, text):
        return '<font style="background-color: %s; color: %s">%s</font>' % \
                (qApp.palette().color(QPalette.Window).name(),
                 qApp.palette().color(QPalette.WindowText).name(),
                 text)

class CompletableLineEdit(QTextEdit):
    tryToComplete = pyqtSignal()
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
                if self.textCursor().atEnd():
                    self.tryToComplete.emit()
            return True
        else:
            return QTextEdit.event(self, event)
    
    def keyPressEvent(self, event):
        self._clearInlineCompletion()
        QTextEdit.keyPressEvent(self, event)
        if self.textCursor().atEnd():
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
        
        self._list = QListView(self)
        self._model = ListModel()
        self._list.setModel(self._model)
        self._list.setItemDelegate(HTMLDelegate())
        self.layout().addWidget(self._list)
        
        self._edit = CompletableLineEdit(self)
        self.layout().addWidget(self._edit)
        self._edit.tryToComplete.connect(self._tryToComplete)
        self.setFocusProxy(self._edit)
        
        #self._list.hide()
        self._edit.setFocus()

    def _tryToComplete(self):
        text = self._edit.toPlainText()
        completion = Completion(text)
        inline = completion.inline()
        if inline:
            self._edit.setInlineCompletion(inline)
        self._model.setCompletion(completion)


import os
import os.path

class Completion:
    def __init__(self, text):
        self._originalText = text
        self._dirs = []
        self._files = []
        self._error = None
        
        text = text.lstrip()
        
        self._relative = text is None or \
                         (not text.startswith('/') and not text.startswith('~'))
        
        if text.startswith('/'):
            absPath = text
        elif text.startswith('~'):
            absPath = os.path.expanduser(text)
        else:  # relative path
            absPath = os.path.abspath(os.path.join(os.path.curdir, text))
        
        if os.path.isdir(absPath):
            absPath += '/'
        
        self.path = os.path.normpath(os.path.dirname(absPath))

        basename = os.path.basename(text)
        
        if os.path.isdir(self.path):
            # filter matching
            try:
                variants = [path for path in os.listdir(self.path) \
                                if path.startswith(basename) and \
                                   not path.startswith('.')]
                
                for variant in variants:
                    if os.path.isdir(os.path.join(self.path, variant)):
                        self._dirs.append(variant + '/')
                    else:
                        self._files.append(variant)
                self._dirs.sort()
                self._files.sort()
            except OSError, ex:
                self._error = unicode(str(ex), 'utf8')
        else:
            self._error = 'No directory %s' % self.path
        
        self._items = []
        if self._error:
            self._items.append(('error', self._error))
        else:
            self._items.append(('currentDir', self.path))
            for dirPath in self._dirs:
                dirPathNoSlash = os.path.split(dirPath)[0]
                parDir, dirName = os.path.split(dirPathNoSlash)
                self._items.append(('directory', dirName + '/'))
            for filePath in self._files:
                fileName = os.path.split(filePath)[1]
                self._items.append(('file', fileName))

    def count(self):
        return len(self._items)
    
    def item(self, index):
        return self._items[index]

    def lastTypedSegmentLength(self):
        """For /home/a/Docu lastTypedSegmentLength() is len("Docu")
        """
        return len(os.path.split(self._originalText)[1])
    
    def _commonStart(self, a, b):
        for index, char in enumerate(a):
            if len(b) <= index or b[index] != char:
                return a[:index]
        return a

    def inline(self):
        if self._error is not None:
            return None
        else:
            if self._dirs or self._files:
                commonPart = reduce(self._commonStart, self._dirs + self._files)
                return commonPart[self.lastTypedSegmentLength():]
            else:
                return ''


def main():
    app = QApplication(sys.argv)
    w = CommandConsole()
    w.show()
    return app.exec_()

if __name__ == '__main__':
    main()
