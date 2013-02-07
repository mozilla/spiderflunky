from nose.tools import eq_

from spiderflunky.parser import parse, ast_iter


def test_ast_iter_order():
    """Test a contrived case where we can test that the visitation order it
    right."""
    ast = {'a': 1, 'body': [{'a': 2, 'body': [{'a': 3, 'body': []}]},
                            {'a': 4, 'body': []}]}
    eq_([node['a'] for node in ast_iter(ast)], [1, 2, 3, 4])


def test_ast_iter_smoke():
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
    ast, _ = parse(js)
