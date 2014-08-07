from funcy import group_by, constantly, walk, identity


FUNC_GROUP = constantly('function')
VAR_GROUP = constantly('variable')
CALL_GROUP = constantly('call')
SYM_GROUP = constantly('symbol')
NONE_GROUP = constantly('None')

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


def _categorize(node):
    return GROUPS.get(node.get('type'), NONE_GROUP)(node)


def categorize(ast):
    return group_by(_categorize, ast.walk_down())


PROCESS = {
}


def process((group, vals)):
    return map(PROCESS.get(group, identity), vals)


def transform(ast):
    return walk(process, categorize(ast))
