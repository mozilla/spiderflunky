import codecs
import os
import re
import subprocess
import tempfile
from functools import partial

import simplejson as json

from spiderflunky.js_ast import Node


class JsReflectException(Exception):
    """Raised when something goes wrong with parsing using Reflect.parse"""

    def __init__(self, value, line=None):
        self.value = value
        self.line = line

    def __unicode__(self):
        return 'Line %i: %s' % (self.line, self.value)

    def __str__(self):
        return self.__unicode__().encode('utf-8')


ERROR_CODE = 100


def parse(code, shell='js'):
    return raw_parse(code, shell)


def raw_parse(code, shell):
    """Return an AST of the JS passed in ``code`` in native Reflect.parse
    format

    :arg shell: Path to the ``js`` interpreter

    """
    code = prepare_code(code)

    temp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
    temp.write(code.encode("utf_8"))
    temp.flush()

    data = """
    try{options("allow_xml");}catch(e){}
    try{
        print(JSON.stringify(Reflect.parse(read(%s))));
        quit(0);
    } catch(e) {
        print(JSON.stringify({
            "error":true,
            "error_message":e.toString(),
            "line_number":e.lineNumber
        }));
        quit(%d);
    }""" % (json.dumps(temp.name), ERROR_CODE)

    try:
        cmd = [shell, "-e", data]
        shell_obj = subprocess.Popen(
            cmd, shell=False,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)

        data, _ = shell_obj.communicate()
        error_code = shell_obj.returncode
        
        if data == "":
            raise JsReflectException("Reflection failed: No AST outputted")

        if error_code not in (0, 3, 100):
            raise RuntimeError('Error calling %r: %s' % (cmd, data))

        data = decode(data)

        parsed = json.loads(data, strict=False, object_hook=lambda x: Node(x))

        if error_code == ERROR_CODE:
            if parsed.get("error"):
                if parsed["error_message"].startswith("ReferenceError: Reflect"):
                    raise RuntimeError("Spidermonkey version too old; "
                                       "1.8pre+ required; error='%s'; "
                                       "spidermonkey='%s'" % (parsed["error_message"],
                                                              shell))
                else:
                    raise JsReflectException(parsed["error_message"],
                                             line=parsed["line_number"])

        # Closing the temp file will delete it.
    finally:
        try:
            temp.close()
            os.unlink(temp.name)
        except IOError:
            pass
    return parsed


JS_ESCAPE = re.compile("\\\\+[ux]", re.I)


def prepare_code(code):
    """Prepare code for tree generation."""
    code = decode(code)
    # Acceptable unicode characters still need to be stripped. Just remove the
    # slash: a character is necessary to prevent bad identifier errors.
    return JS_ESCAPE.sub("u", code)


# From https://github.com/mattbasta/app-validator/blob/ac8e0163f00ad1f989f4d08d59a6e8d51d5c6d2b/appvalidator/unicodehelper.py:

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
    except UnicodeDecodeError:
        pass

    # Test for latin_1, because it can be matched as UTF-16
    # Somewhat of a hack, but it works and is about a thousand times faster
    # than using chardet.
    if all(ord(c) < 256 for c in data):
        try:
            return unicode(data, "latin_1")
        except UnicodeDecodeError:
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

def is_ctrl_char(x, y=None):
    "Returns whether X is an ASCII control character"
    if y is None:
        y = ord(x)
    return 0 <= y <= 31 and y not in (9, 10, 13) # TAB, LF, CR

def is_standard_ascii(x):
    """Returns whether X is a standard, non-control ASCII character"""
    y = ord(x)
    return not (is_ctrl_char(x, y) or y > 126)
