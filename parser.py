import codecs
import simplejson as json
from logging import getLogger
import os
import re
import subprocess
import tempfile


JS_ESCAPE = re.compile("\\\\+[ux]", re.I)


class JsReflectException(Exception):
    """Raised when something goes wrong with parsing using Reflect.parse"""

    def __init__(self, value, line=None):
        self.value = value
        self.line = line

    def __unicode__(self):
        return 'Line %i: %s' % (self.line, self.value)

    def __str__(self):
        return self.__unicode__().encode('utf-8')


def prepare_code(code):
    """Prepare code for tree generation."""
    code = decode(code)
    # Acceptable unicode characters still need to be stripped. Just remove the
    # slash: a character is necessary to prevent bad identifier errors.
    return JS_ESCAPE.sub("u", code)


def parse(code, **kwargs):
    """Return an AST of some JS in native Reflect.parse format along with a map
    of IDs to nodes.

    :arg shell: Path to the ``js`` interpreter

    """
    ast = raw_parse(code, **kwargs)
    by_id = _add_ids(ast)
    _add_parent_refs(ast)
    return ast, by_id


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
    parsed = json.loads(data, strict=False)

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
    """Yield nodes from an AST in depth-first pre-order.
    
    The AST we get from Reflect.parse is somewhat unsatisfying. It's not a
    uniform tree shape; it seems to have already been turned into more
    specialized objects. Thus, we have to traverse into different fields
    depending on node type.
    
    """
    yield ast
    for child in _node_children(ast):
        # Just a "yield from":
        for ret in ast_iter(child):
            yield ret


def _node_children(ast):
    """Return the children of an AST node, accounting for variations in where
    children are stored in each node type."""
    # For some node types, 'body' is a list; for others, an object.
    children = ast.get('body')
    if children is None:
        children = ast.get('expression')  # for ExpressionStatements
    if not children:
        children = []
    elif not isinstance(children, list):
        # Fields like "expression" point to a single object.
        children = [children]
    return children


def _add_ids(ast):
    """Add an ``_id`` key to each node in an AST so we can represent graphs of
    them economically, and return a map of those IDs to the nodes."""
    # TODO: Rename and have it add (weak) parent ptrs as well. We'll need those
    # when figuring out the scopes of variables.
    ret = {}
    for node in ast_iter(ast):
        identity = node['_id'] = id(node)
        ret[identity] = node
    return ret


def _add_parent_refs(ast):
    """Add parent pointers to each node in an AST."""
    for child in _node_children(ast):
        child['_parent'] = ast
        _add_parent_refs(child)
