
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
            self._items.append(('error', self._error))
        else:
            self._items.append(('currentDir', self.path))
            if self._dirs or self._files:
                for dirPath in self._dirs:
                    dirPathNoSlash = os.path.split(dirPath)[0]
                    parDir, dirName = os.path.split(dirPathNoSlash)
                    self._items.append(('directory', dirName + '/'))
                for filePath in self._files:
                    fileName = os.path.split(filePath)[1]
                    self._items.append(('file', fileName))
            else:
                self._items.append(('message', 'No matching files'),)

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

