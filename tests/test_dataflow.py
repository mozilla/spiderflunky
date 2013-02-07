from nose.tools import eq_

from spiderflunky.dataflow import assignments, scope_of
from spiderflunky.parser import parse


def test_assignments():
    js = """a = 8;
            b = a;
            
            function c() {
                var d;
                d = a;
            }"""
    eq_([(a['left']['name'],
          a['right'].get('name', a['right'].get('value'))) for a in
         assignments(parse(js))],
        [('a', 8), ('b', 'a'), ('d', 'a')])
    # TODO: Catch "var a = 8;".


def test_scope_of_global():
    """Make sure the scope of a global is the entire program."""
    js = """a = 0;"""
    ast = parse(js)
    assignment = next(assignments(ast))
    eq_(scope_of(assignment['left']['name'], assignment), ast)
