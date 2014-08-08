from funcy import first
from nose import SkipTest
from nose.tools import eq_

from spiderflunky.dataflow import assignments
from spiderflunky.parser import parse
from spiderflunky.js_ast import walk_down


def test_assignments():
    js = """a = 8;
            b = a;

            function c() {
                var d;
                d = a;
            }"""
    raise SkipTest
    eq_([(a['left']['name'],
          a['right'].get('name', a['right'].get('value'))) for a in
         assignments(parse(js))],
        [('a', 8), ('b', 'a'), ('d', 'a')])


def test_scope_of_global():
    """Make sure the scope of a global is the entire program."""
    js = """a = 0;"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['left']['name'])['type'], 'Program')


def test_scope_of_global_function():
    js = """function smoo() {
                var a;
                a = 0;
            }"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['left']['name'])['type'], 'FunctionDeclaration')


def test_scope_of_inner_reference():
    js = """function smoo() {
                var a;

                function bar() {
                    a = 0;
                }
            }"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['left']['name'])['id']['name'], 'smoo')


def test_scope_of_inner_function():
    js = """function smoo() {
                function bar() {
                    a = 0;
                }
            }"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['left']['name'])['type'], 'Program')


def test_scope_of_inner_function():
    js = """function smoo() {
                function bar() {
                    var a;
                    a = 0;
                }
            }"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['left']['name'])['id']['name'], 'bar')


def test_scope_of_initialized_variable():
    js = """function smoo() {
                var a = 0;
            }"""
    ast = parse(js)
    raise SkipTest
    assignment = first(assignments(ast))
    eq_(assignment.scope_of(assignment['id']['name'])['id']['name'], 'smoo')
 
