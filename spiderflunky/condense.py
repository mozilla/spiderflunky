import json
import subprocess

from collections import namedtuple
from itertools import ifilter, chain, imap

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

Span = namedtuple('Span', ['start', 'end'])
Position = namedtuple('Position', ['offset', 'row', 'col'])
FuncSig = namedtuple('FuncSig', ['input', 'output'])

class SpanVisitor(NodeVisitor):
    def visit_num(self, node, _):
        return int(node.text)

    def visit_pos(self, _, (_0, row, _1, col, _2)):
        return (row, col)

    def visit_span(self, _, (off1, (row1, col1), __, off2, (row2, col2))):
        return Span(Position(off1, row1, col1), Position(off2, row2, col2))

    def generic_visit(self, _, __):
        return None

span_grammar = Grammar("""
span = num pos "-" num pos
pos = "[" num ":" num "]"
num = ~r"\d+"
""")

class ValueVisitor(NodeVisitor):
    def visit_val(self, node, (val,)):
        return val if val else node.text

    def visit_list(self, _, (_1, _type, _2)):
        return "[" + _type + "]"

    def visit_type(self, node, (child,)):
        return child if child else node.text

    def visit_func(self, _, (_1, _2, args, _3, _type)):
        if _type == []:
            _type = [None]
        return FuncSig(args, _type[0])

    def visit_arg(self, _, (name, _type, _2)):
        return (name, _type[0] if _type else None)

    def visit_arg_type(self, node, (_, val)):
        return val

    def visit_output(self, _, (_1, val)):
        return val

    def visit_name(self, node, _):
        return node.text

    def visit_qname(self, node, _):
        return node.text

    def generic_visit(self, _, children):
        return children

def create_handler(grammar, visitor):
    visitor_inst = visitor()
    return lambda x : visitor_inst.visit(grammar.parse(x))

value_grammar = Grammar("""
val = func / list / qname / name
qname = name ":" (qname / name)
func = "fn" "(" args ")" output?
output = " -> " val
args = arg*
arg = name arg_type? ", "?
arg_type = (": " val)
name = ~r"[+?!\.\w<>]+"
list = "[" val "]"
""")

handlers = {
    '!name': str,
    '!url': str,
    '!doc': str,
    '!span': create_handler(span_grammar, SpanVisitor),
    '!type': create_handler(value_grammar, ValueVisitor),
    '!define': str,
    '!effects': str,
    '!proto': str,
    '!stdProto': str,
}

def hook(d):
    d2 = dict(d)
    for key, val in d.items():
        if key.startswith('!'):
            d2[key] = handlers[key](val)
    return d2

# Not in Python 2.6 :(
def check_output(*popenargs, **kwargs):
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    return output

def get_condensed(fpath, condense_path):
    """Return dictionary from ternjs' condensed output."""
    condensed = check_output([condense_path, fpath])
    return json.loads(condensed, object_hook=hook)

def symbols(condensed):
    """Return a dict, (symbol name) -> (dict of fields and metadata)."""
    queue = condensed.items()
    while len(queue) != 0:
        key, val = queue.pop()
        if key.startswith('!'):
            continue
        yield key, val
        if hasattr(val, 'items'):
            queue.extend(val.items())

def is_function((_, obj)):
    if '!type' not in obj:
        return False
    _type = obj['!type']
    return hasattr(_type, 'input') and hasattr(_type, 'output')

def functions(condensed):
    """Return a dict (function name) -> (dict of metadata)."""
    return ifilter(is_function, symbols(condensed))

def _properties((name, obj)):
    if not hasattr(obj, 'items'):
        return []
    return ((name, k) for k in obj.keys() if not k.startswith('!'))

def properties(condensed):
    """Return a list of pairs [(object name, property)]"""
    return chain.from_iterable(imap(_properties, symbols(condensed)))
