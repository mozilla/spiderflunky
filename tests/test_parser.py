from more_itertools import first
from nose.tools import eq_

from spiderflunky.parser import parse, Node


def test_walk_down_order():
    """Test a contrived case where we can test that the visitation order it
    right."""
    ast = Node({'a': 1, 'body': [Node({'a': 2, 'body': [Node({'a': 3, 'body': []})]}),
                                 Node({'a': 4, 'body': []})]})
    eq_([node['a'] for node in ast.walk_down()], [1, 2, 3, 4])


def test_walk_down_smoke():
    """Try it on some real code, and make sure it doesn't crash.

    Here, some nodes have bodies that are lists and others have bodies that are
    objects.

    """
    js = """function answer() {}

            function call() {
                answer();
            }

            call();
            """
    ast = parse(js)


def test_scope_building():
    """Make sure we find all the declarations within a function but don't stray
    into inner functions."""
    js = """function smoo() {
                var w, x;
                
                if (true) {
                    var y;
                }
                
                function bar() {
                    var z;
                }
            }"""
    ast = parse(js)
    function = first(node for node in ast.walk_down() if
                     node['type'] == 'FunctionDeclaration')
    eq_(function.scope(), set(['w', 'x', 'y']))
