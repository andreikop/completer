from PyQt4.QtCore import Qt
from PyQt4.QtGui import qApp, QFileSystemModel, QPalette, QStyle

import os
import os.path

from htmldelegate import htmlEscape

_fsModel = QFileSystemModel()

class PathCompleter:
    
    _ERROR = 'error'
    _CURRENT_DIR = 'currentDir'
    _STATUS = 'status'
    _DIRECTORY = 'directory'
    _FILE = 'file'
    
    def __init__(self, text, pos):
        self._originalText = text
        self._dirs = []
        self._files = []
        self._error = None
        self._status = None
        
        self._relative = text is None or \
                         (not text.startswith('/') and not text.startswith('~'))
        
        enterredDir = os.path.dirname(text)
        enterredFile = os.path.basename(text)
        
        if enterredDir.startswith('/'):
            pass
        elif text.startswith('~'):
            enterredDir = os.path.expanduser(enterredDir)
        else:  # relative path
            enterredDir = os.path.abspath(os.path.join(os.path.curdir, enterredDir))
        
        self.path = os.path.normpath(enterredDir)
        if self.path != '/':
            self.path += '/'

        if not os.path.isdir(self.path):
            self._status = 'No directory %s' % self.path
            return

        try:
            filesAndDirs = os.listdir(self.path)
        except OSError, ex:
            self._error = unicode(str(ex), 'utf8')
            return
        
        if not filesAndDirs:
            self._status = 'Empty directory'
            return
        
        # filter matching
        variants = [path for path in filesAndDirs\
                        if path.startswith(enterredFile) and \
                           not path.startswith('.')]
        for variant in variants:
            if os.path.isdir(os.path.join(self.path, variant)):
                self._dirs.append(variant + '/')
            else:
                self._files.append(variant)
        self._dirs.sort()
        self._files.sort()
        if not self._dirs and not self._files:
            self._status = 'No matching files'

    def _formatPath(self, text):
        typedLen = self._lastTypedSegmentLength()
        typedLenPlusInline = typedLen + len(self.inline())
        return '<b>%s</b><u>%s</u>%s' % \
            (htmlEscape(text[:typedLen]),
             htmlEscape(text[typedLen:typedLenPlusInline]),
             htmlEscape(text[typedLenPlusInline:]))

    def _formatCurrentDir(self, text):
        return '<font style="background-color: %s; color: %s">%s</font>' % \
                (qApp.palette().color(QPalette.Window).name(),
                 qApp.palette().color(QPalette.WindowText).name(),
                 htmlEscape(text))

    def _classifyRowIndex(self, row):
        if self._error:
            assert row == 0
            return (self._ERROR, 0)
        
        if row == 0:
            return (self._CURRENT_DIR, 0)
        
        row -= 1
        if self._status:
            if row == 0:
                return (self._STATUS, 0)
            row -= 1
        
        if row in range(len(self._dirs)):
            return (self._DIRECTORY, row)
        row -= len(self._dirs)
        
        if row in range(len(self._files)):
            return (self._FILE, row)
        
        assert False

    def rowCount(self):
        if self._error:
            return 1
        else:
            count = 1  # current directory
            if self._status:
                count += 1
            count += len(self._dirs)
            count += len(self._files)
            return count

    def columnCount(self):
        return 1
    
    def text(self, row, column):
        rowType, index = self._classifyRowIndex(row)
        if rowType == self._ERROR:
            return '<font color=red>%s</font>' % htmlEscape(self._error)
        elif rowType == self._CURRENT_DIR:
            return self._formatCurrentDir(self.path)
        elif rowType == self._STATUS:
            return '<i>%s</i>' % htmlEscape(self._status)
        elif rowType == self._DIRECTORY:
            dirPath = self._dirs[index]
            dirPathNoSlash = os.path.split(dirPath)[0]
            parDir, dirName = os.path.split(dirPathNoSlash)
            return self._formatPath(dirName + '/')
        elif rowType == self._FILE:
            filePath = self._files[index]
            fileName = os.path.split(filePath)[1]
            return self._formatPath(fileName)

    def icon(self, row, column):
        rowType, index = self._classifyRowIndex(row)
        if rowType == self._ERROR:
            return qApp.style().standardIcon(QStyle.SP_MessageBoxCritical)
        elif rowType == self._CURRENT_DIR:
            return None
        elif rowType == self._STATUS:
            return None
        elif rowType == self._DIRECTORY:
            path = os.path.join(self.path, self._dirs[index])
            index = _fsModel.index(path)
            return _fsModel.data(index, Qt.DecorationRole)
        elif rowType == self._FILE:
            path = os.path.join(self.path, self._files[index])
            index = _fsModel.index(path)
            return _fsModel.data(index, Qt.DecorationRole)

    def _lastTypedSegmentLength(self):
        """For /home/a/Docu _lastTypedSegmentLength() is len("Docu")
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
                return commonPart[self._lastTypedSegmentLength():]
            else:
                return ''

    def inlineForRow(self, row):
        row -= 1  # skip current directory
        if row in range(len(self._dirs)):
            return self._dirs[row][self._lastTypedSegmentLength():]
        else:
            row -= len(self._dirs)  # skip dirs
            if row in range(len(self._files)):
                return self._files[row][self._lastTypedSegmentLength():]
        