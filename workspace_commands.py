import os.path

from pyparsing import CharsNotIn, Combine, Keyword, Literal, Optional, Or, ParseException, \
                     StringEnd, Suppress, White, Word, nums

from pathcompleter import PathCompleter
from locator import AbstractCommand


class CommandGotoLine(AbstractCommand):
    
    @staticmethod
    def signature():
        return '[l] [LINE]'
    
    @staticmethod
    def description():
       return 'Go to line'

    @staticmethod
    def pattern():
        line = Word(nums)("line")
        pat = (Literal('l ') + Suppress(Optional(White())) + Optional(line)) ^ line
        pat.leaveWhitespace()
        pat.setParseAction(CommandGotoLine.create)
        return pat
    
    @staticmethod
    def create(str, loc, tocs):
        if tocs.line:
            line = int(tocs.line)
        else:
            line = None
        return [CommandGotoLine(line)]

    @staticmethod
    def isAvailable():
        return True

    def __init__(self, line):
        self.line = line
    
    def completer(self, text, pos):
        return None

    def isReadyToExecute(self):
        return self.line is not None

    def execute(self):
        print 'goto', self.line


class CommandOpen(AbstractCommand):
    
    @staticmethod
    def signature():
        return '[f] PATH [LINE]'
    
    @staticmethod
    def description():
       return 'Open file'
    
    @staticmethod
    def pattern():
        def attachLocation(s, loc, tocs):
            return [(loc, tocs[0])]

        path = CharsNotIn(" \t")("path")
        path.setParseAction(attachLocation)
        longPath = CharsNotIn(" \t", min=2)("path")
        longPath.setParseAction(attachLocation)
        slashPath = Combine(Literal('/') + Optional(CharsNotIn(" \t")))("path")
        slashPath.setParseAction(attachLocation)

        pat = ((Literal('f ') + Optional(White()) + Optional(path)) ^ longPath ^ slashPath) + \
                    Optional(White() + Word(nums)("line"))
        pat.leaveWhitespace()
        pat.setParseAction(CommandOpen.create)
        return pat

    @staticmethod
    def create(str, loc, tocs):
        if tocs.path:
            pathLocation, path = tocs.path
        else:
            pathLocation, path = 0, ''
        
        if tocs.line:
            line = int(tocs.line)
        else:
            line = None
        
        return [CommandOpen(pathLocation, path, line)]

    @staticmethod
    def isAvailable():
        return True
    
    def __init__(self, pathLocation, path, line):
        self.path = path
        self.pathLocation = pathLocation
        self.line = line
    
    def completer(self, text, pos):
        if pos == self.pathLocation + len(self.path) or \
           (not self.path and pos == len(text)):
            return PathCompleter(self.path, pos - self.pathLocation)
        else:
            return None

    def isReadyToExecute(self):
        return os.path.isfile(os.path.expanduser(self.path))

    def execute(self):
        print 'open file', self.path, self.line


class CommandSaveAs(AbstractCommand):
    
    @staticmethod
    def signature():
        return 's PATH'
    
    @staticmethod
    def description():
       return 'Save file As'
    
    @staticmethod
    def pattern():
        def attachLocation(s, loc, tocs):
            return [(loc, tocs[0])]

        path = CharsNotIn(" \t")("path")
        path.setParseAction(attachLocation)

        pat = (Literal('s ') + Optional(White()) + Optional(path))
        pat.leaveWhitespace()
        pat.setParseAction(CommandSaveAs.create)
        return pat

    @staticmethod
    def create(str, loc, tocs):
        if tocs.path:
            pathLocation, path = tocs.path
        else:
            pathLocation, path = 0, ''
        
        return [CommandSaveAs(pathLocation, path)]

    @staticmethod
    def isAvailable():
        return True
    
    def __init__(self, pathLocation, path):
        self.path = path
        self.pathLocation = pathLocation
    
    def completer(self, text, pos):
        if pos == self.pathLocation + len(self.path) or \
           (not self.path and pos == len(text)):
            return PathCompleter(self.path, pos - self.pathLocation)
        else:
            return None

    def isReadyToExecute(self):
        return len(self.path) > 0

    def execute(self):
        print 'save file as', self.path
