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
    # End when you detect a cycle.