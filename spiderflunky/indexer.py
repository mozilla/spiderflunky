"""Index the Spider Monkey AST.

Uses the same intermediate representation used in DXR's clang plugin.
The transform function is the main entry point for the conversion.

The structure of the IR is a grouping of AST node types with dictionaries
of metadata.

"""
from funcy import group_by, walk, identity, merge


FUNC_GROUP = 'function'
ARROW_GROUP = 'arrow'
VAR_GROUP = 'variable'
CALL_GROUP = 'call'
SYM_GROUP = 'symbol'
NONE_GROUP = 'None'


# mapping type -> GROUP
GROUPS = {
    'Function': FUNC_GROUP,
    'FunctionExpression': FUNC_GROUP,
    'FunctionDeclaration': FUNC_GROUP,
    'ArrowExpression': ARROW_GROUP,
    'VariableDeclaration': VAR_GROUP,
    'LetStatement': VAR_GROUP,
    'LetExpression': VAR_GROUP,
    'CallExpression': CALL_GROUP,
    'Identifier': SYM_GROUP
}


def _categorize(node):
    """Return which group node belongs to."""
    return GROUPS.get(node.get('type'), NONE_GROUP)


def categorize(ast):
    """Group ast nodes based on their type."""
    return group_by(_categorize, ast.walk_down())


def add_span(node):
    """
    Adds span based on location. Is guaentied to work for any node
    """
    return {'span': node['loc']}


# mapping GROUP -> (node -> metadata)
PROCESS = {
    FUNC_GROUP: lambda node: {'name': node['id']['name']},
    VAR_GROUP: lambda node: {'name': node.children()[0]['id']['name']},
    ARROW_GROUP: lambda _: {},
    CALL_GROUP: lambda _: {},
    SYM_GROUP: lambda node: {'name': node['name']},
}


def process((group, nodes)):
    """Based on the group, transform a list a nodes int a list of metadata."""
    process_val = lambda node: merge(
        add_span(node), PROCESS.get(group, identity)(node))
    return group, map(process_val, nodes)


def transform(ast):
    """Transform AST into grouped (by node type) dictionary of metadata dicts.

    """
    return walk(process, categorize(ast))
