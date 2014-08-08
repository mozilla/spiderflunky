"""Contains code pertaining to the JS AST representation.

This is generated based on the Mozilla Parser API at import time.

"""
import pkg_resources

from pyquery import PyQuery
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from funcy import constantly, is_mapping, ifilter, flatten, iflatten
from toposort import toposort_flatten


CALL_EXPR = "CallExpression"
FUNC_EXPR = "FunctionExpression"
IDENT = "Identifier"
PROGRAM = "Program"
ASSIGN_EXPR = "AssignmentExpression"
VAR_DECLARATOR = "VariableDeclarator"
FUNC_DECL = "FunctionDeclaration"


def is_node(item):
    """Tests whether item is a node."""
    return is_mapping(item) and "type" in item


def walk_down(root, skip=constantly(False), include_self=True):
    """Yield each node from here downward, myself included,
    in depth-first pre-order.

    :arg skip: A predicate decribing nodes to not descend into. We always
        return ourselves, even if the predicate says to skip us.
    :arg include_self: A flag for including the root in the walk down.

    The AST we get from Reflect.parse is somewhat unsatisfying. It's not a
    uniform tree shape; it seems to have already been turned into more
    specialized objects. Thus, we have to traverse into different fields
    depending on node type.

    """
    if include_self:
        yield root
    for child in ifilter(is_node, iflatten(root.itervalues())):
        if skip(child):
            yield child
            continue
        # Just a "yield from":
        for ret in walk_down(child, skip=skip):
            yield ret


def _clean(text):
    """Change \xa0 with space."""
    return text.replace(u'\xa0', u' ')


def get_specs(parser, parser_api_htm):
    """Return a list of specs (the results of the SpecVisitor)
    based on Mozilla ParserAPI.

    parser: parser for the grammar
    filename: location of the Mozilla Parser API
    """
    specs = (_clean(elem.text) for elem in PyQuery(parser_api_htm)('pre'))
    visitor = SpecVisitor()
    for spec in (s for s in specs if s.lstrip().startswith('interface')):
        yield visitor.visit(parser.parse(spec))


def process_spec(specs):
    """Builds mapping class -> set of all descendants."""
    tree = dict((name, set(children)) for name, children, _ in specs)
    attr_map = dict((name, attrs) for name, _, attrs in specs)
    for node in toposort_flatten(tree):
        children = tree[node]
        for child in set(children):
            tree[node] |= tree[child]
    return tree, attr_map


API_GRAMMAR = r"""
start = _ interface _
interface = "interface" __ id _ inherit? _ "{" _ attrs? _ "}"

ops = '"' op '"' (_ "|" _ ops)?
op = ~r'([^{}"\s])+'

inherit = "<:" __ parents
parents = id _ ("," _ parents)?

attr = id _ ":" _ vals
attrs = attr _ ";" _ attrs?

vals = val (_ "|" _ vals)?
val = "string" / "null" / "boolean" / dict / list / qid / uint / id
qid = '"' id '"'
list = "[" _ vals _ "]"
dict = "{" _ dict_attrs _ "}"
dict_attrs = attr _ ("," _ dict_attrs)?

uint = "uint32" (_ op _ digit)?

id = ~r"[A-Za-z]+"
digit = ~r"[0-9]+"
_ = ~r"\s*"
__ = ~r"\s+"
"""


class SpecVisitor(NodeVisitor):
    """Implements a NodeVisitor for the Mozilla Parser API."""
    def visit_start(self, _, (_0, interface, _1)):
        """Parse start rule, really just whitespace padding for interface."""
        return interface

    def visit_interface(self, _, (_0, _1, name, _2, maybe_inherit, _3, _4,
                                  _5, maybe_attrs, _6, _7)):
        """Parse the name, inheritance, and attributes for an interface."""
        inherit = maybe_inherit[0] if maybe_inherit else []
        attrs = maybe_attrs[0] if maybe_attrs else []
        return (name, inherit, attrs)

    def visit_inherit(self, _, (_0, _1, parents)):
        """Get all of the interfaces this interface inherits from."""
        return parents

    def visit_parents(self, _, (name, _0, more_parents)):
        """Parse inheritance list."""
        return [name] + flatten(more_parents)

    def visit_attrs(self, _, (attr, _0, _1, _2, attrs)):
        """Return list of all attributes of an interface."""
        return [attr] + (attrs[0] if attrs else [])

    def visit_attr(self, _, children):
        """Parse attribute."""
        # task throw away attr if its static like type
        return children[0]

    def visit_id(self, node, _):
        """Grab the identifier that was match."""
        return node.match.group()

    def generic_visit(self, _, visited_children):
        """Just pass through the children."""
        return visited_children


# Inject INHERITANCE from spec into module
api_parser = Grammar(API_GRAMMAR)
PARSER_API_HTML = pkg_resources.resource_string(__name__, "Parser_API.html")
INHERIT, ATTR_MAP = process_spec(list(get_specs(api_parser, PARSER_API_HTML)))
