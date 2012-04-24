"""
workspace_commands --- Open, SaveAs, GotoLine commands
======================================================
"""

import os.path
import glob

from pyparsing import CharsNotIn, Combine, Keyword, Literal, Optional, Or, ParseException, \
                     StringEnd, Suppress, White, Word, nums

from pathcompleter import makeSuitableCompleter, PathCompleter
from locator import AbstractCommand


class CommandGotoLine(AbstractCommand):
    """Go to line command implementation
    """
    @staticmethod
    def signature():
        """Command signature. For Help
        """
        return '[l] [LINE]'
    
    @staticmethod
    def description():
        """Command description. For Help
        """
        return 'Go to line'

    @staticmethod
    def pattern():
        """Pyparsing pattern
        """
        line = Word(nums)("line")
        pat = (Literal('l ') + Suppress(Optional(White())) + Optional(line)) ^ line
        pat.leaveWhitespace()
        pat.setParseAction(CommandGotoLine.create)
        return pat
    
    @staticmethod
    def create(str, loc, tocs):
        """Callback for pyparsing. Creates an instance of command
        """
        if tocs.line:
            line = int(tocs.line)
        else:
            line = None
        return [CommandGotoLine(line)]

    @staticmethod
    def isAvailable():
        """Check if command is currently available
        """
        return True

    def __init__(self, line):
        self.line = line
    
    def isReadyToExecute(self):
        """Check if command is complete and ready to execute
        """
        return self.line is not None

    def execute(self):
        """Execute the command
        """
        print 'goto', self.line


class CommandOpen(AbstractCommand):
    
    @staticmethod
    def signature():
        """Command signature. For Help
        """
        return '[f] PATH [LINE]'
    
    @staticmethod
    def description():
        """Command description. For Help
        """
        return 'Open file. Globs are supported'
    
    @staticmethod
    def pattern():
        """pyparsing pattern
        """
        
        def attachLocation(s, loc, tocs):
            """pyparsing callback. Saves path position in the original string
            """
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
        """pyparsing callback. Creates an instance of command
        """
        if tocs.path:
            pathLocation, path = tocs.path
        else:
            pathLocation, path = 0, ''
        
        if tocs.line:
            line = int(tocs.line)
        else:
            line = None
        
        return [CommandOpen(pathLocation, path, line)]

    def __init__(self, pathLocation, path, line):
        self.path = path
        self.pathLocation = pathLocation
        self.line = line
    
    def completer(self, text, pos):
        """Command completer.
        If cursor is after path, returns PathCompleter or GlobCompleter 
        """
        if pos == self.pathLocation + len(self.path) or \
           (not self.path and pos == len(text)):
            return makeSuitableCompleter(self.path, pos - self.pathLocation)
        else:
            return None

    def isReadyToExecute(self):
        """Check if command is complete and ready to execute
        """
        return glob.glob(os.path.expanduser(self.path))

    def execute(self):
        """Execute the command
        """
        for path in glob.iglob(os.path.expanduser(self.path)):
            print 'open file', path, self.line


class CommandSaveAs(AbstractCommand):
    """Save As Locator command
    """
    
    @staticmethod
    def signature():
        """Command signature. For Help
        """
        return 's PATH'
    
    @staticmethod
    def description():
        """Command description. For Help
        """
        return 'Save file As'
    
    @staticmethod
    def pattern():
        """pyparsing pattern of the command
        """
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
        """Callback for pyparsing. Creates an instance
        """
        if tocs.path:
            pathLocation, path = tocs.path
        else:
            pathLocation, path = 0, ''
        
        return [CommandSaveAs(pathLocation, path)]

    @staticmethod
    def isAvailable():
        """Check if command is available.
        It is available, if at least one document is opened
        """
        return True
    
    def __init__(self, pathLocation, path):
        self.path = path
        self.pathLocation = pathLocation
    
    def completer(self, text, pos):
        """Command Completer.
        Returns PathCompleter, if cursor stays after path
        """
        if pos == self.pathLocation + len(self.path) or \
           (not self.path and pos == len(text)):
            return PathCompleter(self.path, pos - self.pathLocation)
        else:
            return None

    def isReadyToExecute(self):
        """Check if command is complete and ready to execute
        """
        return len(self.path) > 0

    def execute(self):
        """Execute command
        """
        print 'save file as', self.path
