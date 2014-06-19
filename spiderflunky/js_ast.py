"""Contains code pertaining to the JS AST representation. This is generated
based on the Mozilla Parser API at import time.

"""

from pyquery import PyQuery
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import ParseError
from more_itertools import first
from toposort import toposort_flatten
from itertools import repeat, izip
import sys
import pkg_resources


class BaseNode(dict):
    """A wrapper around a native Reflect.parse dict providing some convenience
    methods and some caching of expensive computations

    Importing a zillion helper functions into every module is a pain.

    """
    def __init__(self, parent, *args, **kwargs):
        super(BaseNode, self).__init__(*args, **kwargs)
        self.parent = parent

    def walk_up(self):
        """Yield each node from here to the root of the tree, starting with
        myself."""
        node = self
        while node:
            yield node
            node = node.parent

    def walk_down(self, skip=lambda n: False, include_self=True):
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
            yield self
        for child in self.children():
            if skip(child):
                yield child
                continue
            # Just a "yield from":
            for ret in child.walk_down(skip=skip):
                yield ret

    def _children(self):
        return []

    def children(self):
        """Return my children, accounting for variations in where children are
        stored in each node type.

        """
        return self._children()

    def nearest_scope(self):
        """Return the closest containing scope, constructing and caching it
        first if necessary.

        """
        return self.nearest_scope_holder().scope()

    def scope_chain(self):
        """Yield each scope-defining node from myself upward."""
        node = self.nearest_scope_holder()
        while True:
            yield node
            if isinstance(node, Program):
                break
            node = node.parent.nearest_scope_holder()

    def nearest_scope_holder(self):
        """Return the nearest node that can have its own scope, potentially
        including myself.

        This will be either a FunctionDeclaration or a Program (for now).

        """
        return first(n for n in self.walk_up() if
                     isinstance(n, (FunctionDeclaration, Program)))

    def scope_of(self, symbol_name):
        """Return the nearest enclosing AST node (including myself) where the
        variable named ``symbol_name`` is defined.

        """
        for node in self.scope_chain():
            if symbol_name in node.scope():
                return node
        # TODO: this might actually be a bug. If its not in the program's scope its undefined
        return node  # global

    def scope(self,):
        """Return the set of symbols declared exactly at this node."""
        return dict()

    def __hash__(self):
        return id(self)


def _clean(text):
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


def dependency_order(specs):
    dep_map = dict((name,set(parents)) for (name, parents, _) in specs)
    return toposort_flatten(dep_map)


def get_class_map(specs):
    """Based on a list of specifications, return a mapping name->cls."""
    dep_order = dependency_order(specs)
    spec_map = dict((name, (parents, vals)) for name, parents, vals in specs)
    class_map = {}
    for name in dep_order:
        class_map[name] = _node_class_factory(class_map, name, *spec_map[name])
    return class_map


def _flatten(lis):
    """Flattens nonuniform nested iterators."""
    # based on http://stackoverflow.com/a/2158532
    for elem in lis:
        if isinstance(elem, list):
            for sub in _flatten(elem):
                yield sub
        else:
            yield elem


def _hoisted_scope(tree):
    return dict((node['id']['name'], node) for node
                in tree.walk_down(skip=lambda n: isinstance(n, FunctionDeclaration))
                if isinstance(node, (VariableDeclarator, FunctionDeclaration)))

def function_scope(self):
    """Return the set of symbols declared exactly at this node."""
    # We store a set of symbols at each node that can hold a scope, except
    # that we don't bother for the Program (global) scope. It holds
    # everything we couldn't find elsewhere.
    # TODO look at 'kind' of variable declaration

    if '_scope' not in self:  # could store this in an instance var
        # Find all the var decls within me, but don't go within any other
        # functions. This implements hoisting.
        self['_scope'] = dict((self, param['name']) for param in self['params'])
        self['_scope'].update(_hoisted_scope(self))
    return self['_scope']

def program_scope(self):
    if '_scope' not in self:  # could store this in an instance var
        # Find all the var decls within me, but don't go within any other
        # functions. This implements hoisting.
        self['_scope'] = _hoisted_scope(self)
    return self['_scope']


def function_repr(self):
    if self['id'] is None:
        return str(None)
    return self['id']['name']


def _node_class_factory(class_map, name, parents, fields):
    """Return a class representing an AST node."""
    # Could perhaps be replaced by an explicit MetaClass
    def _children(self):
        fields_vals = filter(lambda val: isinstance(val, BaseNode),
                             _flatten(self[f] for f in fields))
        return fields_vals

    __dict__ = {'_children': _children}
    if "params" in fields:
        __dict__['scope'] = function_scope
        __dict__['__repr__'] = function_repr

    elif name == "Program":
        __dict__['scope'] = program_scope
        __dict__['__repr__'] = lambda self: "Program"

    bases = tuple(map(class_map.get, parents)) if parents else (BaseNode,)
    return type(str(name), bases, __dict__)


def set_parents(root):
    """Set the parent attribute for all nodes in the tree.
    Root's parent is None

    """
    queue = [(root, None)]
    while queue:
        node, parent = queue.pop()
        node.parent = parent
        queue.extend(izip(node.children(), repeat(node)))


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
    """Implements a NodeVisitor for the Mozilla Parser API
    Returns (name of interface, parents, fields)

    """
    def visit_start(self, node, (_, interface, __)):
        return interface

    def visit_interface(self, node, (_0, _1, name, _2, maybe_inherit, _3, _4,
                                     _5, maybe_attrs, _6, _7)):
        inherit = maybe_inherit[0] if maybe_inherit else []
        attrs = maybe_attrs[0] if maybe_attrs else []
        return (name, inherit, attrs)

    def visit_inherit(self, _, (__, ___, parents)):
        return parents

    def visit_parents(self, _, (name, __, next_parent)):
        return [name]

    def visit_attrs(self, _, (attr, __, ___, ____, attrs)):
        return [attr] + (attrs[0] if attrs else [])

    def visit_attr(self, _, children):
        # task throw away attr if its static like type
        return children[0]

    def visit_id(self, node, _):
        return node.match.group()

    def generic_visit(self, _, visited_children):
        return visited_children

api_parser = Grammar(API_GRAMMAR)


def node_hook(json_dict):
    """This is a object hook for the json loads function.

    """
    return class_map.get(json_dict.get('type'), BaseNode)(None, json_dict)

# Inject classes from spec into module
PARSER_API_HTML = pkg_resources.resource_string(__name__, "Parser_API.html")

class_map = get_class_map(list(get_specs(api_parser, PARSER_API_HTML)))
this_module = sys.modules[__name__]
for cls_name, cls in class_map.items():
    setattr(this_module, cls_name, cls)
