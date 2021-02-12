from collections import namedtuple
from numbers import Number
from vectordatasource import util
from vectordatasource.meta import function
import ast
import astformatter
import os.path
import sys
import yaml


# this captures the end result of processing a layer's yaml
# layer: name of layer
# ast: ast parsed function
# fn: compiled callable
FunctionData = namedtuple('FunctionData', 'layer ast fn')


# stores any useful state along the way as the values have been parsed
class AstState(object):

    def __init__(self, has_way_area, has_volume, has_zoom):
        self.has_way_area = has_way_area
        self.has_volume = has_volume
        self.has_zoom = has_zoom


def parse_case(ast_state, orig):
    assert isinstance(orig, list)

    # make a copy so that we can modify it and not cause problems with any
    # other references to the same list which might exist elsewhere (e.g: with
    # YAML aliases)
    c = list(orig)

    expr = ast.Name('None', ast.Load())
    if len(c) == 0:
        return expr

    if len(c) > 1:
        if c[-1].keys() == ['else']:
            last = c.pop()
            expr = ast_value(ast_state, last['else'])

    for case in reversed(c):
        assert isinstance(case, dict)
        assert set(case.keys()) == set(['when', 'then'])
        cond = create_rules_from_branch(case['when'])
        when = ast_value(ast_state, cond)
        then = ast_value(ast_state, case['then'])
        expr = ast.IfExp(when, then, expr)

    return expr


def parse_call(ast_state, c):
    assert set(c.keys()) == set(('args', 'func'))
    args = c['args']
    func = c['func']
    args_ast = [ast_value(ast_state, x) for x in args]
    # split function on '.' to allow access to namespaced functions (e.g: util)
    func_parts = func.split('.')
    name = ast.Name(func_parts.pop(0), ast.Load())
    while func_parts:
        attr = func_parts.pop(0)
        name = ast.Attribute(value=name, attr=attr, ctx=ast.Load())
    return ast.Call(name, args_ast, [], None, None)


def parse_clamp(ast_state, c):
    assert set(c.keys()) == set(('min', 'max', 'value'))

    min_val = ast_value(ast_state, c['min'])
    max_val = ast_value(ast_state, c['max'])
    value = ast_value(ast_state, c['value'])

    # clamp between min and max values, i.e:
    # max(min_val, min(max_val, value)).
    inner = ast.Call(
        ast.Name('min', ast.Load()),
        [max_val, value],
        [], None, None)

    return ast.Call(
        ast.Name('max', ast.Load()),
        [min_val, inner],
        [], None, None)


def parse_sum(ast_state, orig):
    assert isinstance(orig, list)
    assert len(orig) > 1

    # make a copy so that we can modify it and not cause problems with any
    # other references to the same list which might exist elsewhere (e.g: with
    # YAML aliases)
    s = list(orig)

    left = ast_value(ast_state, s.pop())
    while s:
        right = ast_value(ast_state, s.pop())
        left = ast.BinOp(left, ast.Add(), right)

    return left


# known operators for table lookup
_KNOWN_OPS = {
    '>=': ast.GtE,
    '<=': ast.LtE,
    '==': ast.Eq,
}


def parse_lookup(ast_state, lookup):
    assert isinstance(lookup, dict)
    assert set(lookup.keys()) >= set(('key', 'op', 'table'))

    key = ast_value(ast_state, lookup['key'])

    # only support >=, <= for now
    assert lookup['op'] in _KNOWN_OPS, '%r is not one of %r known binary ' \
        'operators' % (lookup['op'], _KNOWN_OPS.keys())
    op = _KNOWN_OPS[lookup['op']]()

    default = ast_value(ast_state, lookup.get('default'))

    table = lookup['table']
    assert isinstance(table, list)

    expr = default
    for entry in reversed(table):
        assert isinstance(entry, list)
        assert len(entry) == 2
        output, cond = entry
        test = ast.Compare(key, [op], [ast_value(ast_state, cond)])
        expr = ast.IfExp(test, ast_value(ast_state, output), expr)

    return expr


def parse_func(ast_state, name, m):
    assert isinstance(m, list)

    args = [ast_value(ast_state, x) for x in m]

    return ast.Call(
        ast.Name(name, ast.Load()),
        args, [], None, None)


def parse_mul(ast_state, orig):
    assert isinstance(orig, list)
    assert len(orig) > 1

    # make a copy so that we can modify it and not cause problems with any
    # other references to the same list which might exist elsewhere (e.g: with
    # YAML aliases)
    m = list(orig)

    expr = ast_value(ast_state, m.pop())
    while m:
        val = ast_value(ast_state, m.pop())
        expr = ast.BinOp(expr, ast.Mult(), val)

    return expr


def ast_value(ast_state, val):
    if isinstance(val, str):
        return ast.Str(val)
    elif isinstance(val, unicode):
        return ast.Str(val.encode('utf8'))
    elif isinstance(val, dict):
        if val.keys() == ['col']:
            return ast_column(ast_state, val['col'])
        elif val.keys() == ['expr']:
            raise Exception('expr not supported in %r' % val)
        elif val.keys() == ['lit']:
            raise Exception('literal SQL not supported in %r' % val)
        elif 'case' in val.keys():
            return parse_case(ast_state, val['case'])
        elif val.keys() == ['call']:
            return parse_call(ast_state, val['call'])
        elif val.keys() == ['clamp']:
            return parse_clamp(ast_state, val['clamp'])
        elif val.keys() == ['sum']:
            return parse_sum(ast_state, val['sum'])
        elif val.keys() == ['lookup']:
            return parse_lookup(ast_state, val['lookup'])
        elif val.keys() == ['min']:
            return parse_func(ast_state, 'min', val['min'])
        elif val.keys() == ['max']:
            return parse_func(ast_state, 'max', val['max'])
        elif val.keys() == ['mul']:
            return parse_mul(ast_state, val['mul'])
        else:
            return ast.Dict([ast_value(ast_state, k) for k in val.keys()],
                            [ast_value(ast_state, v) for v in val.values()])
    elif isinstance(val, (int, float)):
        return ast.Num(val)
    elif hasattr(val, 'as_ast') and callable(val.as_ast):
        return val.as_ast(ast_state)
    elif val is None:
        return ast.Name('None', ast.Load())
    elif isinstance(val, list):
        return ast.List([ast_value(ast_state, v) for v in val], ast.Load())
    else:
        raise Exception("Don't understand AST value of %r" % val)


def untag_col(col):
    tags = 'tags->'
    if col.startswith(tags):
        col = col[len(tags):]
    return col


def ast_column(ast_state, col):
    col = untag_col(col)
    if col == 'volume':
        ast_state.has_way_area = True
        ast_state.has_volume = True
        result = ast.Name('volume', ast.Load())
    elif col == 'way_area':
        ast_state.has_way_area = True
        result = ast.Name('way_area', ast.Load())
    elif col == 'zoom':
        ast_state.has_way_area = True
        ast_state.has_zoom = True
        result = ast.Name('zoom', ast.Load())
    elif col == 'fid':
        result = ast.Name('fid', ast.Load())
    elif col == 'shape':
        result = ast.Name('shape', ast.Load())
    elif col.startswith('meta.'):
        meta_fields = col.split('.', 1)
        meta_prop = meta_fields[1]
        result = ast.Attribute(
            ast.Name('meta', ast.Load()), meta_prop, ast.Load())
    else:
        result = ast.Call(
            ast.Attribute(
                ast.Name('props', ast.Load()),
                'get',
                ast.Load()),
            [ast.Str(col)],
            [], None, None)
    return result


class EqualsRule(object):

    def __init__(self, column, value):
        self.column = column
        self.value = value

    def as_ast(self, ast_state):
        return ast.Compare(ast_column(ast_state, self.column),
                           [ast.Eq()],
                           [ast_value(ast_state, self.value)])


class GreaterOrEqualsRule(object):
    def __init__(self, column, value):
        self.column = column
        self.value = value

    def as_ast(self, ast_state):
        return ast.Compare(ast_column(ast_state, self.column),
                           [ast.GtE()],
                           [ast_value(ast_state, self.value)])


class SetRule(object):

    def __init__(self, column, values):
        self.column = column
        self.values = values

    def as_ast(self, ast_state):
        values = ast.Tuple(
            [ast_value(ast_state, v) for v in self.values], ast.Load())
        return ast.Compare(ast_column(ast_state, self.column),
                           [ast.In()],
                           [values])


class ExistsRule(object):

    def __init__(self, column):
        self.column = column

    def as_ast(self, ast_state):
        return ast.Compare(ast.Str(untag_col(self.column)),
                           [ast.In()],
                           [ast.Name('props', ast.Load())])


class NotExistsRule(object):

    def __init__(self, column):
        self.column = column

    def as_ast(self, ast_state):
        return ast.Compare(ast_column(ast_state, self.column),
                           [ast.Is()],
                           [ast.Name('None', ast.Load())])


class AndRule(object):

    def __init__(self, rules):
        self.rules = rules

    def as_ast(self, ast_state):
        return ast.BoolOp(
            ast.And(),
            [ast_value(ast_state, r) for r in self.rules])


class OrRule(object):

    def __init__(self, rules):
        self.rules = rules

    def as_ast(self, ast_state):
        return ast.BoolOp(
            ast.Or(),
            [ast_value(ast_state, r) for r in self.rules])


class NotRule(object):

    def __init__(self, rule):
        self.rule = rule

    def as_ast(self, ast_state):
        return ast.UnaryOp(
            ast.Not(),
            ast_value(ast_state, self.rule))


def map_geom_type(geom_type):
    titled = geom_type.title()
    if titled == 'Line':
        titled = 'LineString'
    result = (titled, 'Multi' + titled)
    return result


class GeomTypeRule(object):

    def __init__(self, geom_type):
        assert geom_type in ('point', 'line', 'polygon')
        self.geom_type = geom_type

    def as_ast(self, ast_state):
        attr = ast.Attribute(
            ast.Name('shape', ast.Load()),
            'type',
            ast.Load()
        )
        geom_types = map_geom_type(self.geom_type)
        geom_types_ast = map(ast.Str, geom_types)
        result = ast.Compare(
            attr, [ast.In()], [ast.Tuple(geom_types_ast, ast.Load())])
        return result


def create_rules_from_branch(filter_level, combinator=AndRule):
    # helper to create rules by recursing down an particular branch
    rules = []
    if not isinstance(filter_level, list):
        filter_level = [filter_level]
    for filter_level_item in filter_level:
        for k, v in filter_level_item.items():
            rule = create_filter_rule(k, v)
            rules.append(rule)
    assert rules, 'No rules specified in level: %s' % filter_level
    if len(rules) > 1:
        rule = combinator(rules)
    else:
        rule = rules[0]
    return rule


def create_filter_rule(filter_key, filter_value):
    # check for the composite rules first
    if filter_key == 'not':
        rule = create_rules_from_branch(filter_value)
        rule = NotRule(rule)
    elif filter_key == 'all':
        rule = create_rules_from_branch(filter_value)
    elif filter_key == 'any':
        rule = create_rules_from_branch(filter_value, combinator=OrRule)
    else:
        # leaf rules
        col = filter_key
        if isinstance(filter_value, list):
            rule = SetRule(col, filter_value)
        else:
            if filter_value is True:
                rule = ExistsRule(col)
            elif filter_value is False:
                rule = NotExistsRule(col)
            elif isinstance(filter_value, Number):
                rule = EqualsRule(col, filter_value)
            elif isinstance(filter_value, dict) and 'min' in filter_value:
                rule = GreaterOrEqualsRule(col, filter_value['min'])
            elif isinstance(filter_value, dict) and 'expr' in filter_value:
                raise Exception('expr not supported')
            elif col == 'geom_type':
                rule = GeomTypeRule(filter_value)
            else:
                rule = EqualsRule(col, filter_value)
    return rule


class Matcher(object):

    def __init__(self, rule, output):
        self.rule = rule
        self.output = output

    def as_ast(self, ast_state):
        return ast.If(
            self.rule.as_ast(ast_state),
            [ast.Return(
                ast_value(ast_state, self.output))],
            [])


def create_matcher(yaml_datum, output_fn):
    rules = []
    filters = yaml_datum['filter']
    if not isinstance(filters, list):
        filters = [filters]
    for f in filters:
        for k, v in f.items():
            rule = create_filter_rule(k, v)
            rules.append(rule)
    assert rules, 'No filter rules found in %s' % yaml_datum
    if len(rules) > 1:
        rule = AndRule(rules)
    else:
        rule = rules[0]

    output = output_fn(yaml_datum)

    matcher = Matcher(rule, output)
    return matcher


def make_way_area_assignment():
    # generates:
    # way_area = util.calculate_way_area(shape)
    return ast.Assign(
        targets=[ast.Name(id='way_area', ctx=ast.Store())],
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='util', ctx=ast.Load()),
                attr='calculate_way_area', ctx=ast.Load()),
            args=[ast.Name(id='shape', ctx=ast.Load())],
            keywords=[], starargs=None, kwargs=None))


def make_volume_assignment():
    # generates:
    # volume = util.calculate_volume(way_area, props)
    return ast.Assign(
        targets=[ast.Name(id='volume', ctx=ast.Store())],
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='util', ctx=ast.Load()),
                attr='calculate_volume', ctx=ast.Load()),
            args=[
                ast.Name(id='way_area', ctx=ast.Load()),
                ast.Name(id='props', ctx=ast.Load())],
            keywords=[], starargs=None, kwargs=None))


def make_zoom_assignment():
    # generates:
    # zoom = util.calculate_1px_zoom(way_area)
    return ast.Assign(
        targets=[ast.Name(id='zoom', ctx=ast.Store())],
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='util', ctx=ast.Load()),
                attr='calculate_1px_zoom', ctx=ast.Load()),
            args=[
                ast.Name(id='way_area', ctx=ast.Load())],
            keywords=[], starargs=None, kwargs=None))


def parse_layer_from_yaml(
        ast_state, matchers, fn_name):
    stmts = []
    for matcher in matchers:
        # columns in the query should be those needed by the rule, union those
        # needed by the output, minus any which are synthetic and local to the
        # query function.
        stmts.append(matcher.as_ast(ast_state))

    prepend_statements = []
    if ast_state.has_way_area:
        way_area_stmt = make_way_area_assignment()
        prepend_statements.append(way_area_stmt)
    if ast_state.has_volume:
        volume_stmt = make_volume_assignment()
        prepend_statements.append(volume_stmt)
    if ast_state.has_zoom:
        zoom_stmt = make_zoom_assignment()
        prepend_statements.append(zoom_stmt)
    stmts = prepend_statements + stmts

    func = ast.FunctionDef(
        fn_name,
        ast.arguments([
            ast.Name('shape', ast.Param()),
            ast.Name('props', ast.Param()),
            ast.Name('fid', ast.Param()),
            ast.Name('meta', ast.Param()),
        ], None, None, []),
        stmts,
        [])
    return func


def make_empty_ast_state():
    return AstState(False, False, False)


class FilterCompiler(object):

    def __init__(self):
        scope = {}
        import_asts = []

        # add in required functions into scope for call availability
        for func_name in dir(function):
            fn = getattr(function, func_name)
            if callable(fn):
                scope[func_name] = fn
                import_ast = ast.ImportFrom(
                    'vectordatasource.meta.function',
                    [ast.alias(func_name, None)],
                    0,
                )
                import_asts.append(import_ast)

        scope['util'] = util
        utils_import_ast = ast.ImportFrom(
            'vectordatasource',
            [ast.alias('util', None)],
            0,
        )
        import_asts.append(utils_import_ast)

        self.import_asts = import_asts
        self.scope = scope

    def compile(self, matchers, fn_name):
        ast_state = make_empty_ast_state()
        ast_fn = parse_layer_from_yaml(
            ast_state, matchers, fn_name)

        mod = ast.Module([ast_fn])
        mod_with_linenos = ast.fix_missing_locations(mod)
        code = compile(mod_with_linenos, '<string>', 'exec')
        exec code in self.scope
        compiled_fn = self.scope[fn_name]

        return ast_fn, compiled_fn


LayerParseResult = namedtuple(
    'LayerParseResult', 'layer_data import_asts')


def parse_layers(yaml_path, output_fn, fn_name_fn):
    layer_data = []
    layers = ('landuse', 'pois', 'transit', 'water', 'places', 'boundaries',
              'buildings', 'roads', 'earth', 'admin_areas')

    filter_compiler = FilterCompiler()

    for layer in layers:
        file_path = os.path.join(yaml_path, '%s.yaml' % layer)
        with open(file_path) as fh:
            yaml_data = yaml.load(fh)

        matchers = []
        for yaml_datum in yaml_data['filters']:
            matcher = create_matcher(yaml_datum, output_fn)
            matchers.append(matcher)

        fn_name = fn_name_fn(layer)
        ast_fn, compiled_fn = filter_compiler.compile(matchers, fn_name)
        layer_datum = FunctionData(layer, ast_fn, compiled_fn)
        layer_data.append(layer_datum)

    layer_parse_result = LayerParseResult(
        layer_data, filter_compiler.import_asts)
    return layer_parse_result


def make_function_name_props(layer_name):
    return '%s_props' % layer_name


def make_function_name_min_zoom(layer_name):
    return '%s_min_zoom' % layer_name


def has_kind_in_output(yaml_output):
    if isinstance(yaml_output, dict):
        return 'kind' in yaml_output
    elif isinstance(yaml_output, list):
        for x in yaml_output:
            if has_kind_in_output(x):
                return True
        return False
    else:
        assert not 'Unknown yaml output type %s: %s' % (
            type(yaml_output), yaml_output)


def make_yaml_output_dict(yaml_output):
    result = {}
    if isinstance(yaml_output, list):
        for yaml_output_entry in yaml_output:
            yaml_output_entry_dict = make_yaml_output_dict(yaml_output_entry)
            result.update(yaml_output_entry_dict)
    else:
        assert isinstance(yaml_output, dict)
        result.update(yaml_output)
    return result


def output_kind(yaml_datum):
    yaml_output = yaml_datum['output']
    assert has_kind_in_output(yaml_output), \
        "Matcher for %r doesn't contain kind." % yaml_output
    yaml_output_dict = make_yaml_output_dict(yaml_output)
    return yaml_output_dict


def output_min_zoom(yaml_datum):
    min_zoom = yaml_datum['min_zoom']
    assert not isinstance(min_zoom, (str, unicode)), \
        "Min zoom cannot be a string in %r." % yaml_datum
    return min_zoom


def make_function_mapping(generated_dotted_name_module_path):
    result = {}
    import importlib
    mod = importlib.import_module(generated_dotted_name_module_path)
    fn_names = dir(mod)
    for fn_name in fn_names:
        if fn_name.endswith('_props'):
            fn = getattr(mod, fn_name)
            layer = fn_name.rsplit('_', 1)[0]
            result[layer] = fn
    return result


def main(argv=None):
    from vectordatasource.meta import find_yaml_path
    if argv is None:
        argv = sys.argv
    yaml_path = find_yaml_path()

    formatter = astformatter.ASTFormatter()

    all_layer_data = []
    for output_fn, make_fn_name in (
            (output_kind, make_function_name_props),
            (output_min_zoom, make_function_name_min_zoom)):
        layer_parse_result = parse_layers(
            yaml_path, output_fn, make_fn_name)
        all_layer_data.append(layer_parse_result.layer_data)

    for import_ast in layer_parse_result.import_asts:
        print formatter.format(import_ast, mode='exec')

    for layer_data in all_layer_data:
        for layer_datum in layer_data:
            ast_fn = layer_datum.ast
            print formatter.format(ast_fn, mode='exec')


if __name__ == '__main__':
    main()
