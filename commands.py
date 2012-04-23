import os.path

from pyparsing import CharsNotIn, Combine, Keyword, Literal, Optional, Or, ParseException, \
                     StringEnd, Suppress, White, Word, nums

from pathcompleter import PathCompleter
from locator import AbstractCommand

class CommandOpen(AbstractCommand):
    
    signature = '[f] PATH [LINE]'
    description = 'Open file'
    
    def __init__(self, pathLocation, path, line):
        self.path = path
        self.pathLocation = pathLocation
        self.line = line
    
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
    
    def completer(self, text, pos):
        if pos == self.pathLocation + len(self.path) or \
           (not self.path and pos == len(text)):
            return PathCompleter(self.path, pos - self.pathLocation)
        else:
            return None

    def isReadyToExecute(self):
        return os.path.isfile(os.path.expanduser(self.path))

    @staticmethod
    def isAvailable():
        return True
    
    def execute(self):
        print 'open file', self.path, self.line

class CommandGotoLine(AbstractCommand):
    signature = '[l] [LINE]'
    description = 'Go to line'

    def __init__(self, line):
        self.line = line
    
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

    def completer(self, text, pos):
        return None

    def isReadyToExecute(self):
        return self.line is not None

    @staticmethod
    def isAvailable():
        return True

    def execute(self):
        print 'goto', self.line

commands = [cmd for cmd in (CommandGotoLine, CommandOpen) if cmd.isAvailable()]

def parseCommand(text):
    optWs = Optional(White()).suppress()
    pattern = optWs + Or([cmd.pattern() for cmd in commands]) + optWs + StringEnd()
    try:
        res = pattern.parseString(text)
        return res[0]
    except ParseException:
        return None
