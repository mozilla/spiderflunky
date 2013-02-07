from nose.tools import eq_

from spiderflunky.dataflow import assignments
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
