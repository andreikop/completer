#!/usr/bin/env python

import sip
sip.setapi('QString', 2)

from PyQt4.QtCore import pyqtSignal, QSize, Qt
from PyQt4.QtGui import QApplication, QFontMetrics, QPalette, QSizePolicy, QStyle, \
                        QStyleOptionFrameV2, \
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
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        return QtCore.QSize(doc.idealWidth(), doc.size().height())


from PyQt4.QtCore import QAbstractItemModel, QModelIndex

class ListModel(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self._completion = Completion()  # initial, empty

    def index(self, row, column, parent):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def rowCount(self, index):
        return self._completion.count()
    
    def columnCount(self, index):
        return 1
    
    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._completion.item(index.row())
        else:
            return None
    
    def setCompletion(self, completion):
        self._completion = completion
        self.modelReset.emit()

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
        completion = completeText(text)
        inline = completion.inline()
        if inline:
            self._edit.setInlineCompletion(inline)
        self._model.setCompletion(completion)


import os
import os.path

class Completion:
    def __init__(self, originalText=""):
        self.originalText = originalText
        self.dirs = []
        self.files = []
        self.error = None
    
    def count(self):
        if self.error is not None:
            return 1
        else:
            return len(self.dirs) + len(self.files)
    
    def _makeListItem(self, text):
        return '<b>%s</b>%s' % (text[:len(self.originalText)], text[len(self.originalText):])
    
    def _makeError(self, text):
        return '<i>%s</i>' % text
    
    def item(self, index):
        if self.error is not None:
            return self._makeError(self.error)
        elif index < len(self.dirs):
            return self._makeListItem(self.dirs[index])
        else:
            return self._makeListItem(self.files[index - len(self.dirs)])
    
    def _makeInlineCompletion(self, text):
        return text[len(self.originalText):]

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
                return self._makeInlineCompletion(reduce(self._commonStart, self.dirs + self.files))
            else:
                return ''


def completeText(text):
    completion = Completion(text)
    text = os.path.expanduser(text)
    dirname = os.path.dirname(text)
    basename = os.path.basename(text)
    if os.path.isdir(dirname):
        # filter matching
        try:
            variants = [os.path.join(dirname, path) \
                            for path in os.listdir(dirname) \
                                if path.startswith(basename)]
            
            for variant in variants:
                if os.path.isdir(os.path.join(dirname, variant)):
                    completion.dirs.append(variant + '/')
                else:
                    completion.files.append(variant)
        except OSError, ex:
            completion.error = unicode(str(ex), 'utf8')

    return completion

def main():
    app = QApplication(sys.argv)
    w = CommandConsole()
    w.show()
    return app.exec_()

if __name__ == '__main__':
    main()
