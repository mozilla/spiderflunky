from funcy import first
from nose.tools import eq_
from nose import SkipTest

from spiderflunky.js_ast import FUNC_DECL, walk_down
from spiderflunky.parser import parse


def test_walk_down_smoke():
    """Try it on some real code, and make sure it doesn't crash.

    Here, some nodes have bodies that are lists and others have bodies that are
    objects.

    """
    js = """
    function answer() {}
    
    function call() {
        answer();
    }

    call();
    """
    ast = parse(js)


def test_scope_building():
    """Make sure we find all the declarations within a function but don't stray
    into inner functions."""
    js = """
    function smoo() {
        var w, x;
        if (true) {
            var y;
        }
        function bar() {
            var z;
        }
    }
    function barbar() {

    }
    """
    ast = parse(js)
    function = first(node for node in walk_down(ast) if
                     node['type'] == FUNC_DECL)
    raise SkipTest("Need to reimplement scope")
    eq_(set(function.scope().keys()), set(['w', 'x', 'y', 'smoo', 'bar']))

    eq_(set(ast.scope().keys()), set(['smoo', 'barbar']))
