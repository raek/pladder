from collections import namedtuple


class ParseError(Exception):
    pass


Call = namedtuple("Call", "words")
Word = namedtuple("Word", "fragments")
Literal = namedtuple("Literal", "string")


def parse(text):
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text):
        self.text = text
        self.end_pos = len(text)
        self.pos = 0

    def at_end(self):
        return self.pos == self.end_pos

    def pop(self):
        c = self.text[self.pos]
        self.pos += 1
        return c

    def try_pop(self, c):
        if self.at_end():
            return False
        else:
            if self.text[self.pos] == c:
                self.pos += 1
                return True
            else:
                return False

    def try_peek(self, c):
        if self.at_end():
            return False
        else:
            return self.text[self.pos] == c

    def parse(self):
        call = self.parse_call()
        if self.at_end():
            return call
        else:
            raise ParseError("Excessive closing bracket")

    def parse_call(self):
        words = []
        while True:
            self.parse_whitespace()
            if self.at_end() or self.try_peek("]"):
                break
            word = self.parse_word()
            words.append(word)
        return Call(words)

    def parse_whitespace(self):
        while True:
            if not self.try_pop(" "):
                break

    def parse_word(self):
        fragments = []
        fragment_start = self.pos
        while True:
            if self.at_end() or self.try_peek("]") or self.try_peek(" "):
                fragment_end = self.pos
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                break
            elif self.try_pop("["):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                call = self.parse_call()
                if self.at_end():
                    raise ParseError("Missing closing bracket")
                else:
                    assert self.pop() == "]"  # Should always be true
                fragments.append(call)
                fragment_start = self.pos
            else:
                self.pop()
        return Word(fragments)
