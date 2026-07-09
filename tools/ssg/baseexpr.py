from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---- AST -------------------------------------------------------------------

@dataclass
class Lit:
    value: object

@dataclass
class Ref:
    name: str            # dotted, e.g. "price", "file.name", "formula.ppu"

@dataclass
class Unary:
    op: str
    node: object

@dataclass
class Binary:
    op: str
    left: object
    right: object

@dataclass
class Call:
    name: str            # global function
    args: list = field(default_factory=list)

@dataclass
class Method:
    recv: object
    name: str
    args: list = field(default_factory=list)

@dataclass
class Field:
    recv: object
    name: str


# ---- tokenizer -------------------------------------------------------------

_TOKEN_RE = re.compile(r"""
    \s+
  | (?P<num>\d+\.\d+|\d+)
  | (?P<str>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|>=|<=|&&|\|\||[-+*/%<>!().,])
""", re.VERBOSE)


def _tokenize(text):
    tokens, pos = [], 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise _ParseError(f"bad token at {pos}")
        pos = m.end()
        if m.lastgroup is None:  # whitespace
            continue
        tokens.append((m.lastgroup, m.group()))
    tokens.append(("end", ""))
    return tokens


class _ParseError(Exception):
    pass


_KEYWORDS = {"true": True, "false": False, "null": None}

# Heads whose dotted chain stays a single Ref (file.name, note.age,
# formula.ppu). Any other bare identifier's `.ident` access (no call
# following) is a Field instead, e.g. tags.length.
_NAMESPACE_ROOTS = {"file", "note", "formula"}


class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def next(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, value):
        kind, val = self.next()
        if val != value:
            raise _ParseError(f"expected {value!r}, got {val!r}")

    # precedence-climbing for binary operators
    _BIN = [("||",), ("&&",), ("==", "!="), ("<", ">", "<=", ">="),
            ("+", "-"), ("*", "/", "%")]

    def parse_expr(self, level=0):
        if level >= len(self._BIN):
            return self.parse_unary()
        node = self.parse_expr(level + 1)
        while self.peek()[1] in self._BIN[level]:
            op = self.next()[1]
            right = self.parse_expr(level + 1)
            node = Binary(op, node, right)
        return node

    def parse_unary(self):
        kind, val = self.peek()
        if val in ("!", "-"):
            self.next()
            operand = self.parse_unary()
            if val == "-" and isinstance(operand, Lit) and isinstance(operand.value, (int, float)):
                return Lit(-operand.value)
            return Unary(val, operand)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while self.peek()[1] == ".":
            self.next()
            kind, name = self.next()
            if kind != "name":
                raise _ParseError(f"expected name after '.', got {name!r}")
            if self.peek()[1] == "(":
                args = self.parse_args()
                node = Method(node, name, args)
            elif isinstance(node, Ref) and node.name in _NAMESPACE_ROOTS:
                # extend a dotted ref: file.name, note.age, formula.ppu
                node = Ref(node.name + "." + name)
            else:
                node = Field(node, name)
        return node

    def parse_args(self):
        self.expect("(")
        args = []
        if self.peek()[1] != ")":
            args.append(self.parse_expr())
            while self.peek()[1] == ",":
                self.next()
                args.append(self.parse_expr())
        self.expect(")")
        return args

    def parse_primary(self):
        kind, val = self.next()
        if kind == "num":
            return Lit(float(val) if "." in val else int(val))
        if kind == "str":
            return Lit(_unquote(val))
        if kind == "name":
            if val in _KEYWORDS:
                return Lit(_KEYWORDS[val])
            if self.peek()[1] == "(":
                return Call(val, self.parse_args())
            return Ref(val)
        if val == "(":
            node = self.parse_expr()
            self.expect(")")
            return node
        raise _ParseError(f"unexpected {val!r}")


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}


def _unquote(tok):
    body = tok[1:-1]
    if "\\" not in body:
        return body
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse(text):
    """Parse an expression to an AST, or None on any syntax error."""
    if not text or not text.strip():
        return None
    try:
        tokens = _tokenize(text)
        p = _Parser(tokens)
        node = p.parse_expr()
        if p.peek()[0] != "end":
            raise _ParseError(f"trailing input {p.peek()[1]!r}")
        return node
    except _ParseError:
        return None
