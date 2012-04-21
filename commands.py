from pyparsing import CharsNotIn, Keyword, Literal, Optional, Or, ParseException, White, Word, nums

from pathcompleter import PathCompleter

ws = White().suppress()
optWs = Optional(ws).suppress()

class CommandOpen:
    def __init__(self, pathLocation, path):
        self.path = path
        self.pathLocation = pathLocation
    
    @staticmethod
    def pattern():
        def attachLocation(s, loc, tocs):
            return [(loc, tocs[0])]

        path = CharsNotIn(" \t")("path")
        path.setParseAction(attachLocation)
        longPath = CharsNotIn(" \t", min=2)("path")
        longPath.setParseAction(attachLocation)
        slashPath = Literal('/') + Optional(CharsNotIn(" \t"))("path")
        slashPath.setParseAction(attachLocation)

        pat = (Literal('f ') + Optional(path)) ^ longPath ^ slashPath
        pat.leaveWhitespace()
        pat.setParseAction(CommandOpen.create)
        return pat

    @staticmethod
    def create(str, loc, tocs):
        if tocs.path:
            pathLocation, path = tocs.path
        else:
            pathLocation, path = 0, ''
        return [CommandOpen(pathLocation, path)]
    
    def completion(self, pos):
        return PathCompleter(self.path, pos - self.pathLocation)

class CommandGotoLine:
    def __init__(self, line):
        self.line = line
    
    @staticmethod
    def pattern():
        line = Word(nums)("line")
        pat = (Literal('l ') + Optional(line)) ^ line
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

    def completion(self, pos):
        return None

def parseCommand(text):
    commands = (CommandGotoLine, CommandOpen)
    
    pattern = optWs + Or([cmd.pattern() for cmd in commands]) + optWs
    try:
        res = pattern.parseString(text)
        return res[0]
    except ParseException:
        return None
