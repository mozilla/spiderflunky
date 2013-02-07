import codecs
import simplejson as json
from logging import getLogger
import os
import re
import subprocess
import tempfile

from more_itertools import first


class JsReflectException(Exception):
    """Raised when something goes wrong with parsing using Reflect.parse"""

    def __init__(self, value, line=None):
        self.value = value
        self.line = line

    def __unicode__(self):
        return 'Line %i: %s' % (self.line, self.value)

    def __str__(self):
        return self.__unicode__().encode('utf-8')


class Node(dict):
    """A wrapper around a native Reflect.parse dict providing some convenience
    methods and some caching of expensive computations

    Importing a zillion helper functions into every module is a pain.

    """
    def walk_up(self):
        """Yield each node from here to the root of the tree, starting with
        myself."""
        node = self
        while True:
            yield node
            node = node.get('_parent')
            if node is None:
                break

    def walk_down(self, skip=lambda n: False):
        """Yield each node from here downware, myself included, in depth-first
        pre-order.

        :arg skip: A predicate decribing nodes to not descend into. We always
            return ourselves, even if the predicate says to skip us.

        The AST we get from Reflect.parse is somewhat unsatisfying. It's not a
        uniform tree shape; it seems to have already been turned into more
        specialized objects. Thus, we have to traverse into different fields
        depending on node type.

        """
        yield self
        for child in self.children():
            if not skip(child):
                # Just a "yield from":
                for ret in child.walk_down():
                    yield ret

    def _children(self):
        body = self.get('body', [])
        if not isinstance(body, list):
            # For some node types, 'body' is a list; for others, an object.
            body = [body]
        return body

    def children(self):
        """Return my children, accounting for variations in where children are
        stored in each node type."""
        return self._children() or []

    def nearest_scope(self):
        """Return the closest containing Scope, constructing and caching it
        first if necessary."""
        return self._nearest_scope_holder().scope()

    def _nearest_scope_holder(self):
        """Return the nearest node that can have its own scope.

        This will be either a FunctionDeclaration or a Program (for now).

        """
        return first(n for n in self.walk_up() if n['type'] in
                     ['FunctionDeclaration', 'Program'])

    def scope(self):
        """Return the set of symbols declared exactly at this node."""
        # We store a set of symbols at each node that can hold a scope, except
        # that we don't bother for the Program (global) scope.

        # TODO: Maybe move this to a more specific subclass.
        assert self['type'] in ['FunctionDeclaration', 'Program']

        if '_scope' not in self:
            # Find all the var decls within me, but don't go within any other
            # functions. This implements hoisting.
            self['_scope'] = set(
                node['id']['name'] for node in self.walk_down(
                    skip=lambda n: n['type'] == 'FunctionDeclaration')
                if node['type'] == 'VariableDeclarator')
        return self['_scope']


class VariableDeclaration(Node):
    def _children(self):
        return self['declarations']


class ExpressionStatement(Node):
    def _children(self):
        return [self['expression']]


class Ast(Node):
    """A Reflect.parse AST with some other handy properties

    An Ast is considered to be immutable once finalize() is called, though we
    may continue to make annotations on it for speed.

    """
    def finalize(self):
        """Add parent pointers to my nodes, and assemble a map so we can
        reference nodes by ID."""
        def _add_ids(ast):
            """Add an ``_id`` key to each node in me so we can represent graphs of
            them economically, and build a map of those IDs to the nodes."""
            ret = {}
            for node in ast.walk_down():
                identity = node['_id'] = id(node)
                ret[identity] = node
            return ret

        def _add_parent_refs(node):
            """Add parent pointers to each node in me."""
            for child in node.children():
                child['_parent'] = node
                _add_parent_refs(child)

        self.by_id = _add_ids(self)
        _add_parent_refs(self)


NODE_TYPES = {'Program': Ast,
              'ExpressionStatement': ExpressionStatement,
              'VariableDeclaration': VariableDeclaration}
def _make_node(d):
    """Construct the right kind of Node for a raw Reflect.parse node."""
    return NODE_TYPES.get(d.get('type'), Node)(d)


def parse(code, **kwargs):
    """Construct an ``Ast`` of the given JS code.

    :arg shell: Path to the ``js`` interpreter

    """
    ast = Ast(raw_parse(code, **kwargs))
    ast.finalize()
    return ast


def raw_parse(code, shell='js'):
    """Return an AST of the JS passed in ``code`` in native Reflect.parse
    format

    :arg shell: Path to the ``js`` interpreter

    """
    if not code:
        return None

    code = prepare_code(code)

    temp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
    temp.write(code.encode("utf_8"))
    temp.flush()

    data = """
    try{options("allow_xml");}catch(e){}
    try{
        print(JSON.stringify(Reflect.parse(read(%s))));
    } catch(e) {
        print(JSON.stringify({
            "error":true,
            "error_message":e.toString(),
            "line_number":e.lineNumber
        }));
    }""" % json.dumps(temp.name)

    try:
        cmd = [shell, "-e", data]
        shell_obj = subprocess.Popen(
            cmd, shell=False,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)

        data, stderr = shell_obj.communicate()
        if stderr:
            raise RuntimeError('Error calling %r: %s' % (cmd, stderr))

        # Closing the temp file will delete it.
    finally:
        try:
            temp.close()
            os.unlink(temp.name)
        except IOError:
            pass

    if not data:
        raise JsReflectException("Reflection failed")

    data = decode(data)
    parsed = json.loads(data, strict=False, object_hook=_make_node)

    if "error" in parsed and parsed["error"]:
        if parsed["error_message"].startswith("ReferenceError: Reflect"):
            raise RuntimeError("Spidermonkey version too old; "
                               "1.8pre+ required; error='%s'; "
                               "spidermonkey='%s'" % (parsed["error_message"],
                                                      shell))
        else:
            raise JsReflectException(parsed["error_message"],
                                     line=parsed["line_number"])

    return parsed


JS_ESCAPE = re.compile("\\\\+[ux]", re.I)


def prepare_code(code):
    """Prepare code for tree generation."""
    code = decode(code)
    # Acceptable unicode characters still need to be stripped. Just remove the
    # slash: a character is necessary to prevent bad identifier errors.
    return JS_ESCAPE.sub("u", code)


# From https://github.com/mattbasta/app-validator/blob/ac8e0163f00ad1f989f4d08d59a6e8d51d5c6d2b/appvalidator/unicodehelper.py:

import codecs

# Many thanks to nmaier for inspiration and code in this module

UNICODES = [
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    ]

COMMON_ENCODINGS = ("utf-16", "latin_1", "ascii")

def decode(data):
    """
    Decode data employing some charset detection and including unicode BOM
    stripping.
    """

    # Don't make more work than we have to.
    if not isinstance(data, str):
        return data

    # Detect standard unicodes.
    for bom, encoding in UNICODES:
        if data.startswith(bom):
            return unicode(data[len(bom):], encoding, "ignore")

    # Try straight UTF-8
    try:
        return unicode(data, "utf-8")
    except Exception:
        pass

    # Test for latin_1, because it can be matched as UTF-16
    # Somewhat of a hack, but it works and is about a thousand times faster
    # than using chardet.
    if all(ord(c) < 256 for c in data):
        try:
            return unicode(data, "latin_1")
        except Exception:
            pass

    # Test for various common encodings.
    for encoding in COMMON_ENCODINGS:
        try:
            return unicode(data, encoding)
        except UnicodeDecodeError:
            pass

    # Anything else gets filtered.
    return unicode(filter_ascii(data), errors="replace")


def filter_ascii(text):
    if isinstance(text, list):
        return [filter_ascii(x) for x in text]
    return "".join((x if is_standard_ascii(x) else "?") for x in text)


def ast_iter(ast):
    """Yield nodes from an AST in depth-first pre-order."""
    # Deprecated in favor of walk_down().
    return ast.walk_down()
