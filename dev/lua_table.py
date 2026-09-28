"""Read and write the Lua table files the game's api.File uses."""

import re

TOKEN_PATTERN = re.compile(
    r'\s*(?:(?P<string>"(?:\\.|[^"\\])*")'
    r"|(?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<symbol>[{}\[\]=,]))"
)
PLAIN_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
INDENT = "    "


def load(path):
    """Returns the table in the file as a list, or [] if the file is missing or empty."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    value = _Parser(text).read_value()
    if isinstance(value, dict):
        return [value[key] for key in sorted(k for k in value if isinstance(k, int))]
    return value if isinstance(value, list) else []


def save(path, value):
    path.write_text(to_lua(value) + "\n", encoding="utf-8")


def unescape(text):
    return re.sub(r"\\(.)", r"\1", text)


def to_lua(value, depth=0):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    inner_indent = INDENT * (depth + 1)
    lines = []
    if isinstance(value, list):
        for item in value:
            lines.append(f"{inner_indent}{to_lua(item, depth + 1)},")
    elif isinstance(value, dict):
        for key, item in value.items():
            lines.append(f"{inner_indent}{_lua_key(key)} = {to_lua(item, depth + 1)},")
    else:
        raise TypeError(f"Cannot write {type(value).__name__} to Lua")
    return "{\n" + "\n".join(lines) + ("\n" if lines else "") + INDENT * depth + "}"


def _lua_key(key):
    if isinstance(key, str) and PLAIN_KEY_PATTERN.fullmatch(key):
        return key
    return f"[{to_lua(key)}]"


class _Parser:
    def __init__(self, text):
        self.tokens = self._tokenize(text)
        self.position = 0

    @staticmethod
    def _tokenize(text):
        tokens = []
        position = 0
        while position < len(text):
            match = TOKEN_PATTERN.match(text, position)
            if match is None:
                raise ValueError(f"Unexpected text at {position}: {text[position:position + 20]!r}")
            tokens.append((match.lastgroup, match.group(match.lastgroup)))
            position = match.end()
        return tokens

    def _peek(self, offset=0):
        index = self.position + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return (None, None)

    def _next(self, expected=None):
        kind, text = self._peek()
        if expected is not None and text != expected:
            raise ValueError(f"Expected {expected!r}, got {text!r}")
        self.position += 1
        return kind, text

    def read_value(self):
        kind, text = self._next()
        if kind == "string":
            return unescape(text[1:-1])
        if kind == "number":
            return float(text) if any(c in text for c in ".eE") else int(text)
        if text == "true":
            return True
        if text == "false":
            return False
        if text == "nil":
            return None
        if text == "{":
            return self._read_table()
        raise ValueError(f"Unexpected {text!r}")

    def _read_table(self):
        items = []
        fields = {}
        while self._peek()[1] != "}":
            kind, text = self._peek()
            if kind == "word" and self._peek(1)[1] == "=":
                self._next()
                self._next("=")
                fields[text] = self.read_value()
            elif text == "[":
                self._next("[")
                key = self.read_value()
                self._next("]")
                self._next("=")
                fields[key] = self.read_value()
            else:
                items.append(self.read_value())
            if self._peek()[1] == ",":
                self._next(",")
        self._next("}")

        if not fields:
            return items
        for number, item in enumerate(items, start=1):
            fields[number] = item
        return fields
