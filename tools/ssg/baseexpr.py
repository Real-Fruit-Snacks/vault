from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import basefuncs
from .basevalue import BaseError, binary, compare, truthy


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
    except (_ParseError, RecursionError):
        return None


def evaluate(node, ctx):
    """Evaluate an AST against ctx; return None on any evaluation error.

    This is the per-expression graceful-degradation boundary: it catches not
    just BaseError but the ordinary exceptions an unguarded library edge can
    raise (bad args, wrong types), so no base expression can ever crash a
    build. It deliberately does NOT catch KeyboardInterrupt/SystemExit."""
    try:
        return _eval(node, ctx)
    except (BaseError, ValueError, TypeError, IndexError, KeyError,
            AttributeError, ArithmeticError, OverflowError, RecursionError):
        return None


def _eval(node, ctx):
    if node is None:
        return None
    if isinstance(node, Lit):
        return node.value
    if isinstance(node, Ref):
        return ctx.resolve(node.name)
    if isinstance(node, Unary):
        if node.op == "!":
            return not truthy(_eval(node.node, ctx))
        return binary("-", 0, _eval(node.node, ctx))  # unary minus
    if isinstance(node, Binary):
        if node.op == "&&":
            return truthy(_eval(node.left, ctx)) and truthy(_eval(node.right, ctx))
        if node.op == "||":
            return truthy(_eval(node.left, ctx)) or truthy(_eval(node.right, ctx))
        left, right = _eval(node.left, ctx), _eval(node.right, ctx)
        if node.op in ("==", "!=", ">", "<", ">=", "<="):
            return compare(node.op, left, right)
        return binary(node.op, left, right)
    if isinstance(node, Call):
        args = [_eval(a, ctx) for a in node.args]
        return basefuncs.call_global(node.name, args, ctx.build_now)
    if isinstance(node, Method):
        # file.hasTag(...) etc.: check the ctx file hook BEFORE evaluating the
        # receiver, since Ref("file") is not itself a value (would raise).
        fm = getattr(ctx, "file_method", None)
        if fm is not None and _is_file_ref(node.recv):
            handled, result = fm(node.name, [_eval(a, ctx) for a in node.args])
            if handled:
                return result
        recv = _eval(node.recv, ctx)
        args = [_eval(a, ctx) for a in node.args]
        return basefuncs.call_method(recv, node.name, args)
    if isinstance(node, Field):
        recv = _eval(node.recv, ctx)
        return basefuncs.get_field(recv, node.name)
    raise BaseError("unknown node")


def _is_file_ref(node):
    return isinstance(node, Ref) and node.name == "file"


def compile(text):
    """Parse once; return callable(ctx) -> value, or None if it doesn't parse."""
    node = parse(text)
    if node is None:
        return None
    return lambda ctx: evaluate(node, ctx)


def as_predicate(text):
    """Return callable(ctx) -> bool (truthiness), or None if it doesn't parse."""
    node = parse(text)
    if node is None:
        return None
    return lambda ctx: truthy(evaluate(node, ctx))
