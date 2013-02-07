from collections import namedtuple


# scope is an AST node.
ScopedSymbol = namedtuple('ScopedSymbol', ['scope', 'symbol'])


def assignments(ast):
    """Yield each of the assignment statements that could move a function.

    At the moment, we distinguish only by type of operator, but we could leave
    out assignments with literal strings and ints and such on the RHS.

    """
    # TODO: Figure out whether |=, ^=, or &= can move functions or objects
    # containing them.
    return (node for node in ast.walk_down() if
            node['type'] == 'AssignmentExpression' and node['operator'] == '=')


def scope_of(symbol_name, in_node):
    """Return the AST node where the variable named ``symbol_name``, occurring
    in node ``in_node`` is defined."""
    # TODO: Find formal params, lets, and window.* (and navigator.*? Anything
    # else magic? Ugh, and you can stick refs to window in things. Is that
    # going to be a problem?)

    for node in in_node.scope_chain():
        if symbol_name in node.scope():
            return node
    return node  # global


# TODO: We'll also have to watch when objects are created. You can put
# functions in those. We'll have to track what symbol the objects are initially
# assigned to and where they flow from there. Then observe when somebody
# unpacks one and calls it.
