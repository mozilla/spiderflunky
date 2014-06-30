from spiderflunky.condense import FuncSig, Span, Position, symbols, functions, properties

CONDENSED = {u'!name': '/home/mvc/work/spiderflunky/spiderflunky/tests/test_program.js',
             u'answer': {u'!span': Span(start=Position(offset=9, row=0, col=9),
                                        end=Position(offset=15, row=0, col=15)),
                         u'!type': FuncSig(input=[], output=None)},
             u'call': {u'!span': Span(start=Position(offset=31, row=2, col=9),
                                      end=Position(offset=35, row=2, col=13)),
                       u'!type': FuncSig(input=[], output=None)}}

def test_symbols():
    assert set(sym for sym, _ in symbols(CONDENSED)) == set(['answer', 'call'])


def test_functions():
    assert set(name for name, _ in functions(CONDENSED)) <= set(['answer', 'call'])

def test_properties():
    assert set(name for name, _ in properties(CONDENSED)) == set()
