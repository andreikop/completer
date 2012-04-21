from PyQt4.QtGui import qApp, QPalette

import os
import os.path

class PathCompleter:
    def __init__(self, text, pos):
        self._originalText = text
        self._dirs = []
        self._files = []
        self._error = None
        
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

        if os.path.isdir(self.path):
            # filter matching
            try:
                variants = [path for path in os.listdir(self.path) \
                                if path.startswith(enterredFile) and \
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
            self._items.append('<font color=red>%s</font>' % self._error)
        else:
            self._items.append(self._formatCurrentDir(self.path))
            if self._dirs or self._files:
                for dirPath in self._dirs:
                    dirPathNoSlash = os.path.split(dirPath)[0]
                    parDir, dirName = os.path.split(dirPathNoSlash)
                    self._items.append(self._formatPath(dirName + '/'))
                for filePath in self._files:
                    fileName = os.path.split(filePath)[1]
                    self._items.append(fileName)
            else:
                self._items.append('<i>No matching files</i>')

    def _formatPath(self, text):
        typedLen = self._lastTypedSegmentLength()
        typedLenPlusInline = typedLen + len(self.inline())
        return '<b>%s</b><u>%s</u>%s' % \
            (text[:typedLen],
             text[typedLen:typedLenPlusInline],
             text[typedLenPlusInline:])

    def _formatCurrentDir(self, text):
        return '<font style="background-color: %s; color: %s">%s</font>' % \
                (qApp.palette().color(QPalette.Window).name(),
                 qApp.palette().color(QPalette.WindowText).name(),
                 text)

    def rowCount(self):
        return len(self._items)
    
    def columnCount(self):
        return len(self._items)
    
    def item(self, index):
        return self._items[index]

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

    def columnCount(self):
        return 1