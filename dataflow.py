from collections import namedtuple

from spiderflunky.parser import ast_iter


# scope is an AST node.
ScopedSymbol = namedtuple('ScopedSymbol', ['scope', 'symbol'])


def assignments(ast):
    """Yield each of the assignment statements that could move a function."""
    # TODO: Figure out whether |=, ^=, or &= can move functions or objects
    # containing them.
    return (node for node in ast_iter(ast) if
            node['type'] == 'AssignmentExpression' and node['operator'] == '=')
