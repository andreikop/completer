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
        self._completion = Completion(None)  # initial, empty
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
            else:
                return self._formatListItem(item)
        elif role == Qt.DecorationRole:
            if itemType == 'error':
                return qApp.style().standardIcon(QStyle.SP_MessageBoxCritical)
            else:
                index = self._fsModel.index(os.path.join(self._completion.path, item))
                return self._fsModel.data(index, role)
            
        return None
    
    def setCompletion(self, completion):
        self._completion = completion
        self.modelReset.emit()

    def _formatListItem(self, text):
        typedLen = self._completion.lastTypedSegmentLength()
        return '<b>%s</b>%s' % (text[:typedLen], text[typedLen:])

    def _formatError(self, text):
        return '<i>%s</i>' % text


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
            self.insertPlainText(self._inlineCompletion)
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
        self.originalText = text
        self.dirs = []
        self.files = []
        self.error = None
        if text is None or not text:
            return
        
        dirname = os.path.dirname(text)
        self.path = dirname

        basename = os.path.basename(text)
        expandedDir = os.path.expanduser(dirname)
        if os.path.isdir(expandedDir):
            # filter matching
            try:
                variants = [path for path in os.listdir(expandedDir) \
                                if path.startswith(basename)]
                
                for variant in variants:
                    if os.path.isdir(os.path.join(expandedDir, variant)):
                        self.dirs.append(variant + '/')
                    else:
                        self.files.append(variant)
                self.dirs.sort()
                self.files.sort()
            except OSError, ex:
                self.error = unicode(str(ex), 'utf8')
        else:
            self.error = 'No directory %s' % dirname

    def count(self):
        if self.error is not None:
            return 1
        else:
            return len(self.dirs) + len(self.files)
    
    def item(self, index):
        if self.error is not None:
            return 'error', self.error
        elif index < len(self.dirs):
            dirPath = self.dirs[index]
            dirPathNoSlash = os.path.split(dirPath)[0]
            parDir, dirName = os.path.split(dirPathNoSlash)
            return 'directory', dirName + '/'
        else:
            filePath = self.files[index - len(self.dirs)]
            fileName = os.path.split(filePath)[1]
            return 'file', fileName
    
    def lastTypedSegmentLength(self):
        """For /home/a/Docu lastTypedSegmentLength() is len("Docu")
        """
        return len(os.path.split(self.originalText)[1])
    
    def _commonStart(self, a, b):
        for index, char in enumerate(a):
            if len(b) <= index or b[index] != char:
                return a[:index]
        return a

    def inline(self):
        if self.error is not None:
            return None
        else:
            if self.dirs or self.files:
                commonPart = reduce(self._commonStart, self.dirs + self.files)
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
