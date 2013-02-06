#!/usr/bin/env python

import codecs
import simplejson as json
from logging import getLogger
import os
import re
import subprocess
import tempfile


JS_ESCAPE = re.compile("\\\\+[ux]", re.I)
SPIDERMONKEY_INSTALLATION = '/usr/local/bin/js'


class JSReflectException(Exception):
    """An exception to indicate that tokenization has failed."""

    def __init__(self, value):
        self.value = value
        self.line = None

    def __str__(self):
        return repr(self.value)

    def line_num(self, line_num):
        "Set the line number and return self for chaining"
        self.line = int(line_num)
        return self


def prepare_code(code):
    """Prepare code for tree generation."""
    code = decode(code)
    # Acceptable unicode characters still need to be stripped. Just remove the
    # slash: a character is necessary to prevent bad identifier errors.
    return JS_ESCAPE.sub("u", code)


def get_tree(code, shell=SPIDERMONKEY_INSTALLATION):
    """Return an AST tree of the JS passed in `code`."""

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
        raise JSReflectException("Reflection failed")

    data = decode(data)
    parsed = json.loads(data, strict=False)

    if "error" in parsed and parsed["error"]:
        if parsed["error_message"].startswith("ReferenceError: Reflect"):
            raise RuntimeError("Spidermonkey version too old; "
                               "1.8pre+ required; error='%s'; "
                               "spidermonkey='%s'" % (parsed["error_message"],
                                                      shell))
        else:
            raise JSReflectException(parsed["error_message"]).line_num(
                    parsed["line_number"])

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
    except:
        pass

    # Test for latin_1, because it can be matched as UTF-16
    # Somewhat of a hack, but it works and is about a thousand times faster
    # than using chardet.
    if all(ord(c) < 256 for c in data):
        try:
            return unicode(data, "latin_1")
        except:
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



INFINITY = float("inf")


# From https://github.com/mattbasta/app-validator/blob/e474775bfce7ef2ce55b3e1bd3bcacf74f587a30/appvalidator/contextgenerator.py
class ContextGenerator:
    """The context generator creates a line-by-line mapping of all files that
    are validated. It will then use that to help produce useful bits of code
    for errors, warnings, and the like."""

    def __init__(self, data=None):
        self.data = data.split("\n")

    def get_context(self, line=1, column=0):
        """Return a tuple containing the context for a line."""

        line -= 1  # The line is one-based

        # If there is no data in the file, there can be no context.
        datalen = len(self.data)
        if datalen <= line:
            return None

        build = [self.data[line]]

        # Add surrounding lines if they're available. There must always be
        # three elements in the context.
        if line > 0:
            build.insert(0, self.data[line - 1])
        else:
            build.insert(0, None)

        if line < datalen - 1:
            build.append(self.data[line + 1])
        else:
            build.append(None)

        leading_counts = []

        # Count whitespace to determine how much needs to be stripped.
        lstrip_count = INFINITY
        for line in build:
            # Don't count empty/whitespace-only lines.
            if line is None or not line.strip():
                leading_counts.append(lstrip_count)
                continue

            # Isolate the leading whitespace.
            ws_count = len(line) - len(line.lstrip())
            leading_counts.append(ws_count)
            if ws_count < lstrip_count:
                lstrip_count = ws_count

        # If all of the lines were skipped over, it means everything was
        # whitespace.
        if lstrip_count == INFINITY:
            return ("", "", "")

        for lnum in range(3):
            # Skip edge lines.
            if not build[lnum]:
                continue

            line = build[lnum].strip()

            # Empty lines stay empty.
            if not line:
                build[lnum] = ""
                continue

            line = self._format_line(line, column=column, rel_line=lnum)
            line = "%s%s" % (" " * (leading_counts[lnum] - lstrip_count), line)

            build[lnum] = line

        # Return the final output as a tuple.
        return tuple(build)

    def _format_line(self, data, column=0, rel_line=1):
        """Formats a line from the data to be the appropriate length."""
        line_length = len(data)

        if line_length > 140:
            if rel_line == 0:
                # Trim from the beginning
                data = "... %s" % data[-140:]
            elif rel_line == 1:
                # Trim surrounding the error position
                if column < 70:
                    data = "%s ..." % data[:140]
                elif column > line_length - 70:
                    data = "... %s" % data[-140:]
                else:
                    data = "... %s ..." % data[column - 70:column + 70]

            elif rel_line == 2:
                # Trim from the end
                data = "%s ..." % data[:140]

        return decode(data)

    def get_line(self, position):
        """Returns the line number that the given string position is found on."""

        datalen = len(self.data)
        count = len(self.data[0])
        line = 1
        while count < position:
            if line >= datalen:
                break
            count += len(self.data[line]) + 1
            line += 1

        return line


if __name__ == '__main__':
    print get_tree('function frob() {return 8;}')
