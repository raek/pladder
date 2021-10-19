from typing import Callable, List

from .types import Call, Char, Fragment, Literal, ParseError, Variable, Word


def escape(word: str) -> str:
    if word == "" or " " in word or "{" in word:
        return "{" + word + "}"
    else:
        return word


def parse(text: str) -> Call:
    return _Parser(text).parse()


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.end_pos = len(text)
        self.pos = 0

    def at_end(self) -> bool:
        return self.pos == self.end_pos

    def pop(self) -> Char:
        c = self.text[self.pos]
        self.pos += 1
        return c

    def try_pop(self, c: Char) -> bool:
        if self.at_end():
            return False
        else:
            if self.text[self.pos] == c:
                self.pos += 1
                return True
            else:
                return False

    def try_peek(self, c: Char) -> bool:
        if self.at_end():
            return False
        else:
            return self.text[self.pos] == c

    def parse(self) -> Call:
        call = self.parse_call()
        if self.at_end():
            return call
        else:
            raise ParseError("Excessive closing bracket")

    def parse_call(self) -> Call:
        words = []
        while True:
            self.parse_whitespace()
            if self.at_end() or self.try_peek("]"):
                break
            word = self.parse_word()
            words.append(word)
        return Call(words)

    def parse_whitespace(self) -> None:
        while True:
            if not self.try_pop(" "):
                break

    def parse_word(self) -> Word:
        fragments: List[Fragment] = []
        fragment_start = self.pos
        fragment_type: Callable[[str], Fragment] = Literal
        while True:
            if self.at_end() or self.try_peek("]") or self.try_peek(" "):
                fragment_end = self.pos
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                break
            elif self.try_pop("["):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                call = self.parse_call()
                if self.at_end():
                    raise ParseError("Missing closing bracket")
                else:
                    assert self.pop() == "]"  # Should always be true
                fragments.append(call)
                fragment_start = self.pos
                fragment_type = Literal
            elif self.try_pop("{"):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = Literal(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                fragment_start = self.pos
                level = 1
                while not self.at_end():
                    c = self.pop()
                    if c == "{":
                        level += 1
                    elif c == "}":
                        level -= 1
                        if level == 0:
                            break
                if level != 0:
                    raise ParseError("Missing closing brace")
                fragment_end = self.pos - 1
                fragment = Literal(self.text[fragment_start:fragment_end])
                fragments.append(fragment)
                fragment_start = self.pos
                fragment_type = Literal
            elif self.try_pop("}"):
                raise ParseError("Excessive closing brace")
            elif self.try_pop("$"):
                fragment_end = self.pos - 1
                if fragment_start != fragment_end:
                    fragment = fragment_type(self.text[fragment_start:fragment_end])
                    fragments.append(fragment)
                fragment_start = self.pos
                fragment_type = Variable
            else:
                self.pop()
        return Word(fragments)
