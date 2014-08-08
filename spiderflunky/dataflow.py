from collections import namedtuple
from js_ast import Assign_Expr, Var_Declarator


# scope is an AST node.
ScopedSymbol = namedtuple('ScopedSymbol', ['scope', 'symbol'])


def assignments(ast):
    """Yield each of the assignment statements that could move a function.

    At the moment, we distinguish only by type of operator, but we could leave
    out assignments with literal strings and ints and such on the RHS.

    """
    return (node for node in ast.walk_down() if
            (node['type'] == AssignExpr and node['operator'] == '=') or
            (node['type'] == VarDeclarator and node['init'] is not None))


# TODO: We'll also have to watch when objects are created. You can put
# functions in those. We'll have to track what symbol the objects are initially
# assigned to and where they flow from there. Then observe when somebody
# unpacks one and calls it.
