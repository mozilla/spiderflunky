from spiderflunky.js_ast import CALL_EXPR, FUNC_EXPR, IDENT
from spiderflunky.parser import parse

from networkx import DiGraph


def call_sites(ast):
    """Yield the AST nodes representing function calls."""
    return (node for node in ast.walk_down() if isinstance(node, CallExpression))


def call_graph(ast):
    """Return a call graph (networkx.Diagraph) caller ---(callsite)---> callee.

    All values are represented as AST nodes. You can straightforwardly pull
    line and column numbers out and apply them to the original code to get
    excerpts.

    """
    graph = DiGraph()
    for call_site in call_sites(ast):
        graph.add_edge(call_site.nearest_scope_holder(), lookup(call_site),
                       call_site=call_site)
    return graph


def call_sites_for(function_node, graph):
    """Return a list of call-site nodes where a given function node is
    called.

    """
    return (graph.get_edge_data(src, dst)['call_site'] for src, dst 
            in graph.edges() if dst == function_node)


def lookup(call_site):
    """Look up the declaration of this call_site."""
    # Check if scope_of or its children has the same id as the call_site'
    callee = call_site['callee']
    if callee['type'] == FUNC_EXPR):
        if callee['id'] is None:            
            return None
        return callee['id']['name']
    elif callee['type'] == IDENT:
        name = call_site['callee']['name']
        return call_site.scope_of(name).scope().get(name, None)
    else:
        return None


def get_name(node):
    """Return the identifier for this node."""

    if 'id' not in node:
        return str(type(node))

    ident = node['id']
    if ident is None:
        return str(None)
    return ident.get('name', str(None))

    
