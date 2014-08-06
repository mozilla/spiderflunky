from funcy import group_by, constantly


FUNC_GROUP = constantly('function')
VAR_GROUP = constantly('variable')
CALL_GROUP = constantly('call')
SYM_GROUP = constantly('symbol')

GROUPS = {
    'Function': FUNC_GROUP,
    'FunctionExpression': FUNC_GROUP,
    'ArrowExpression': FUNC_GROUP,
    'FunctionDeclaration': FUNC_GROUP,
    'VariableDeclaration': VAR_GROUP,
    'LetStatement': VAR_GROUP,
    'LetExpression': VAR_GROUP,
    'CallExpression': CALL_GROUP,
}


def categorize(node):
    return GROUPS.get(node.get('type'))(node)


def transform(ast):
    return group_by(categorize, ast.walk_down())
