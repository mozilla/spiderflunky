from spiderflunky.parser import parse, ast_iter


def call_sites(ast):
    """Yield the AST nodes representing function calls."""
    return (node for node in ast_iter(ast) if node['type'] == 'CallExpression')


def call_graph(ast):
    """Return an iterable of (callee, callsite, data path through which the
    callee got to the callsite).

    All values are represented as AST nodes. You can straightforwardly pull
    line and column numbers out and apply them to the original code to get
    excerpts.

    """
    # Call scope() on each of the symbols in assignments(), and add an edge from (left symbol name, left scope ID) to (right symbol name, right scope ID). When it terminates in a literal, add a vertex for that; we'll use that to highlight the ultimate answer. There's probably a good way to avoid graphing *all* the assignments (like maybe finding all the call sites and then working backwards up the assignment chain), but that's for later.


def call_sites_for(function_node):
    """Return a list of call-site nodes where a given function node is
    called."""
    # Get the scope() of the function_node, then walk from that vertex of the graph to everywhere you can get, returning each. We might want to put something more descriptive than symbol names and scope nodes in the graph: it would be nice to be able to highlight the actual original value.

    # End when you detect a cycle.
