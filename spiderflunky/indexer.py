from operator import itemgetter

from funcy import group_by, constantly, walk, identity, merge


FUNC_GROUP = 'function'
ARROW_GROUP = 'arrow'
VAR_GROUP = 'variable'
CALL_GROUP = 'call'
SYM_GROUP = 'symbol'
NONE_GROUP = 'None'


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
    return GROUPS.get(node.get('type'), NONE_GROUP)


def categorize(ast):
    return group_by(_categorize, ast.walk_down())


def with_view(tag, view):
    def _with_view(func):
        def __with_view(node):
            return merge({tag: view(node)}, func(node))
        return __with_view
    return _with_view


span_view = with_view('span', itemgetter('loc'))


@span_view
def process_func(node):
    return {'name': node['id']['name']}


@span_view
def process_arrow(_):
    return {}


@span_view
def process_var(node):
    return {'name': node.children()[0]['id']['name']}


@span_view
def process_sym(node):
    return {'name': node['name']}


PROCESS = {
    FUNC_GROUP: process_func,
    VAR_GROUP: process_var,
    ARROW_GROUP: process_arrow,
    CALL_GROUP: identity,
    SYM_GROUP: process_sym,
}


def process((group, vals)):
    return group, map(PROCESS.get(group, identity), vals)


def transform(ast):
    return walk(process, categorize(ast))
