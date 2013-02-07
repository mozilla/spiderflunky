from nose import SkipTest
from nose.tools import eq_

from spiderflunky.calls import call_sites
from spiderflunky.parser import parse


def test_call_sites():
    """Make sure we can find all the call sites in a program."""
    js = """function answer() {}

            function call() {
                answer();
            }

            call();
            """
    ast = parse(js)
    eq_([node['callee']['name'] for node in call_sites(ast)],
        ['answer', 'call'])


def test_simple():
    """Assert we notice simple calls to functions stored in global scope."""
    raise SkipTest
    js = """function answer() {}

            function call() {
                answer();
            }"""
    #ok_(callee definitions, callsite, list of assignments through which is percolated


def test_nested():
    """Assert we identify calls to functions within the calling scope."""
    raise SkipTest
    js = """function call() {
                function answer() {}

                answer();
            }"""


def test_traverse():
    """Show that we can follow a function as it flows through simple
    assignments."""
    raise SkipTest
    js = """function answer() {}

            indirect_answer = answer;

            function call() {
                indirect_answer();
            }"""
