import re
import typing as t


class PeekLines:
    def __init__(self, *, lines: t.Iterator[str], skip_line_patterns: list[re.Pattern]):
        self._lines = lines
        self._skip_line_patterns = skip_line_patterns
        self._next_line = None
        self._next_line_number = 0

    def peek(self):
        while True:
            peek_line_number, peek_line = self._peek()
            if peek_line is None or not any(
                [pattern.match(peek_line) for pattern in self._skip_line_patterns]
            ):
                return peek_line_number, peek_line
            else:
                self._next_line = None

    def _peek(self):
        if self._next_line is None:
            try:
                self._next_line = next(self._lines).strip()
                self._next_line_number += 1
            except StopIteration:
                self._next_line_number = None
        return self._next_line_number, self._next_line

    def peek_starts_with(self, prefix):
        _, next_line = self.peek()
        return next_line is not None and next_line.startswith(prefix)

    def consume(self):
        if self._next_line is None:
            self.peek()
        line_number, line = self._next_line_number, self._next_line
        self._next_line = None
        return line_number, line
