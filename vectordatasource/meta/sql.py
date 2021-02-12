from vectordatasource.meta.python import parse_layers, output_kind, \
        output_min_zoom, LayerParseResult, FunctionData
import sys
import ast
from cStringIO import StringIO


LAYER_TABLES = {
    'boundaries': [
        'ne_10m_admin_0_boundary_lines_land',
        'ne_10m_admin_0_boundary_lines_map_units',
        'ne_10m_admin_0_boundary_lines_disputed_areas',
        'ne_10m_admin_1_states_provinces_lines',
        'ne_110m_admin_0_boundary_lines_land',
        'ne_50m_admin_0_boundary_lines_land',
        'ne_50m_admin_0_boundary_lines_disputed_areas',
        'ne_50m_admin_1_states_provinces_lines',
        'planet_osm_line',
        'planet_osm_polygon',
    ],
    'buildings': [
        'planet_osm_point',
        'planet_osm_polygon',
    ],
    'earth': [
        'land_polygons',
        'ne_10m_land',
        'ne_110m_land',
        'ne_50m_land',
        'planet_osm_line',
        'planet_osm_point',
        'planet_osm_polygon',
    ],
    'landuse': [
        'planet_osm_line',
        'planet_osm_polygon',
        'ne_50m_urban_areas',
        'ne_10m_urban_areas',
    ],
    'places': [
        'ne_10m_populated_places',
        'planet_osm_point',
    ],
    'pois': [
        'planet_osm_point',
        'planet_osm_polygon',
    ],
    'roads': [
        'ne_10m_roads',
        'planet_osm_line',
    ],
    'contours': [
        'contours',
    ],
    'transit': [
        'planet_osm_line',
        'planet_osm_polygon',
    ],
    'water': [
        'ne_10m_coastline',
        'ne_10m_lakes',
        'ne_10m_ocean',
        'ne_10m_playas',
        'ne_110m_coastline',
        'ne_110m_lakes',
        'ne_110m_ocean',
        'ne_50m_coastline',
        'ne_50m_lakes',
        'ne_50m_ocean',
        'ne_50m_playas',
        'planet_osm_line',
        'planet_osm_point',
        'planet_osm_polygon',
        'water_polygons',
    ],
    'admin_areas': [
        'admin_areas',
    ],
}


POLYGON_TABLES = [
    'planet_osm_polygon',
    'buffered_land',
    'land_polygons',
    'ne_10m_lakes',
    'ne_10m_land',
    'ne_10m_ocean',
    'ne_10m_playas',
    'ne_10m_urban_areas',
    'ne_110m_lakes',
    'ne_110m_land',
    'ne_110m_ocean',
    'ne_50m_lakes',
    'ne_50m_land',
    'ne_50m_ocean',
    'ne_50m_playas',
    'ne_50m_urban_areas',
    'water_polygons',
    'admin_areas',
]


ADAPTOR_QUERY = """
CREATE OR REPLACE FUNCTION mz_calculate_%(calc)s_%(layer)s(%(table)s)
RETURNS %(return_type)s AS $$
DECLARE
  row ALIAS FOR $1;
BEGIN
  RETURN mz_calculate_%(calc)s_%(layer)s_(
    row.%(fid_column)s, row.%(geom_column)s, %(tags_expr)s, %(way_area)s,
    '%(meta_source)s');
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

BOOL_OPS = {
    ast.And: "AND",
    ast.Or:  "OR",
}


CMP_OPS = {
    ast.Eq:    "=",
    ast.NotEq: "<>",
    ast.In:    "IN",
    ast.Is:    "IS",
    ast.GtE:   ">=",
    ast.LtE:   "<=",
}


CMP_DEFAULTS = {
    ast.Eq:    "FALSE",
    ast.NotEq: "TRUE",
    ast.In:    "FALSE",
    ast.Is:    "FALSE",
    ast.GtE:   "FALSE",
    ast.LtE:   "FALSE",
}


UNARY_OPS = {
    ast.Not: "NOT ",
}


BINARY_OPS = {
    ast.Add:  "+",
    ast.Mult: "*",
}


VALUES = {
    'props':    'tags',
    'None':     'NULL',
    'volume':   'volume',
    'way_area': 'way_area',
    'shape':    'way',
    'fid':      'fid',
    'zoom':     'zoom',
}


KNOWN_FUNCS = {
    'mz_building_kind_detail':            'mz_building_kind_detail',
    'mz_building_part_kind_detail':       'mz_building_part_kind_detail',
    'trim_nz_sh':                         'trim_nz_sh',
    'mz_get_rel_networks':                'mz_get_rel_networks',
    'util.cycling_network':               'mz_cycling_network',
    'util.calculate_way_area':            'way_area',
    'util.calculate_volume':              'mz_calculate_building_volume',
    'ST_GeometryType':                    'ST_GeometryType',
    'util.calculate_1px_zoom':            'mz_one_pixel_zoom',
    'min':                                'LEAST',
    'max':                                'GREATEST',
    'mz_to_float_meters':                 'mz_to_float_meters',
    'mz_get_min_zoom_highway_level_gate': 'mz_get_min_zoom_highway_level_gate',
    'mz_calculate_path_major_route':      'mz_calculate_path_major_route',
    'mz_calculate_ferry_level':           'mz_calculate_ferry_level',
    'util.is_building':                   'mz_calculate_is_building_or_part',
    'util.tag_str_to_bool':               'notimplemented',
    'util.safe_int':                      'tz_safe_int',
    'util.true_or_none':                  'notimplemented',
    'tz_looks_like_service_area':         'tz_looks_like_service_area',
    'tz_looks_like_rest_area':            'tz_looks_like_rest_area',
    'tz_estimate_parking_capacity':       'tz_estimate_parking_capacity',
}


# this is a bit of a hack to force the type of expressions with least/greatest
# in them to be of numeric type.
FUNC_FORCE_TYPE = {
    'LEAST':    float,
    'GREATEST': float,
}


GLOBALS = [
    'way_area',
]


def instance_lookup(obj, mapping):
    value = None

    for (klass, val) in mapping.items():
        if isinstance(obj, klass):
            value = val
            break

    assert value, "instance lookup for %s" % type(obj)
    return value


def sql_type(expr):
    if isinstance(expr, ast.Name) and \
       expr.id in ('volume'):
        return int
    if isinstance(expr, ast.Call) and \
       isinstance(expr.func, ast.Attribute) and \
       isinstance(expr.func.value, ast.Name) and \
       expr.func.value.id == 'props' and \
       expr.args[0].s in ('scalerank', 'min_zoom'):
        return float
    return str


def sql_as_json(d):
    s = StringIO()

    s.write("{")
    first = True
    for (k, v) in zip(d.keys, d.values):
        if first:
            first = False
        else:
            s.write(", ")
        assert isinstance(k, ast.Str)
        s.write("\"%s\": " % k.s)

        if isinstance(v, ast.Str):
            s.write("\"%s\"" % v.s)
        elif isinstance(v, ast.Num):
            s.write("%d" % v.n)
        elif isinstance(v, ast.Name):
            if v.id == 'None':
                s.write("null")
            else:
                raise RuntimeError("What is a %r?" % v.id)
        elif isinstance(v, (ast.Call, ast.IfExp)):
            s.write("' || mz_to_json_null_safe(")
            s.write(sql_expression(v))
            s.write(") || '")
        else:
            raise RuntimeError("Don't know what to do with %r" % (v,))

    s.write("}")
    return s.getvalue()


def fn_name(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        assert isinstance(node.value, ast.Name)
        return node.value.id + "." + fn_name(node.attr)
    elif isinstance(node, (str, unicode)):
        return node
    else:
        raise RuntimeError("Don't know how to make a function name from %r"
                           % (node,))


class SQLExpression(ast.NodeVisitor):

    def __init__(self, force_type=None):
        self.buf = StringIO()
        self.force_type = force_type
        self.in_json = False

    def visit_BoolOp(self, op):
        self.buf.write("(")
        first = True
        for v in op.values:
            if first:
                first = False
            else:
                val = instance_lookup(op.op, BOOL_OPS)
                self.buf.write(" " + val + " ")
            self.visit(v)
        self.buf.write(")")

    def visit_Compare(self, cp):
        old_type = self.force_type
        typ = sql_type(cp.left)
        self.force_type = None

        self.buf.write("(")

        # special case for IN, since in Python 'x in tuple' and 'x in dict'
        # are treated the same way, but in SQL we have to use different
        # syntax to check if something is in a list or in an hstore.
        if len(cp.ops) == 1 and \
           isinstance(cp.ops[0], ast.In) and \
           isinstance(cp.comparators[0], ast.Name):
            self.visit(cp.comparators[0])
            self.buf.write(" ? ")
            self.visit(cp.left)

        else:
            if len(cp.comparators) != 1:
                raise RuntimeError("Expecting only one comparator, got %d" %
                                   (len(cp.comparators),))

            default = instance_lookup(cp.ops[0], CMP_DEFAULTS)
            self.buf.write("COALESCE(")

            self.force_type = typ
            self.visit(cp.left)

            for (op, v) in zip(cp.ops, cp.comparators):
                val = instance_lookup(op, CMP_OPS)
                self.buf.write(" " + val + " ")
                self.visit(v)

            self.buf.write(",%s)" % (default,))

        self.buf.write(")")
        self.force_type = old_type

    def visit_UnaryOp(self, op):
        self.buf.write("(")
        self.buf.write(instance_lookup(op.op, UNARY_OPS))
        self.visit(op.operand)
        self.buf.write(")")

    def visit_BinOp(self, op):
        self.buf.write("(")
        self.visit(op.left)
        self.buf.write(instance_lookup(op.op, BINARY_OPS))
        self.visit(op.right)
        self.buf.write(")")

    def visit_Str(self, s):
        # TODO: escaping
        if self.force_type == int:
            self.buf.write("'" + s.s + "'::integer")
        elif self.force_type == float:
            self.buf.write("'" + s.s + "'::real")
        else:
            self.buf.write("'" + s.s + "'")

    def visit_Num(self, n):
        if self.force_type == str:
            if isinstance(n.n, float):
                self.buf.write("'%f'" % n.n)
            else:
                self.buf.write("'%d'" % n.n)
        else:
            if isinstance(n.n, float):
                self.buf.write("%f" % n.n)
            else:
                self.buf.write("%d" % n.n)

    def visit_Call(self, call):
        if isinstance(call.func, ast.Attribute) and \
           isinstance(call.func.value, ast.Name) and \
           call.func.value.id == 'props':
            col_name = call.args[0].s
            if "'" in col_name:
                raise RuntimeError("Tag/column name cannot contain "
                                   "single quote: %r" % (col_name,))

            if self.force_type == int:
                self.buf.write("(tags->'%s')::integer" % col_name)
            elif self.force_type == float:
                self.buf.write("(tags->'%s')::real" % col_name)
            else:
                self.buf.write("tags->'%s'" % col_name)
        else:
            name = fn_name(call.func)
            func = KNOWN_FUNCS.get(name)
            if not func:
                raise RuntimeError("Call to name not implemented yet: %r"
                                   % (name,))
            force_type = self.force_type
            self.force_type = FUNC_FORCE_TYPE.get(func)

            self.buf.write(func)
            self.buf.write("(")
            first = True
            for arg in call.args:
                if first:
                    first = False
                else:
                    self.buf.write(", ")
                self.visit(arg)
            self.buf.write(")")

            self.force_type = force_type

    def visit_Name(self, name):
        val = VALUES.get(name.id)
        if val:
            self.buf.write(val)
        else:
            raise RuntimeError("Don't know what name %r means" % name.id)

    def visit_Tuple(self, t):
        self.buf.write("(")
        first = True
        for elt in t.elts:
            if first:
                first = False
            else:
                self.buf.write(", ")
            self.visit(elt)
        self.buf.write(")")

    def visit_Dict(self, d):
        old_in_json = self.in_json
        self.in_json = True
        self.buf.write("('")
        self.buf.write(sql_as_json(d))
        self.buf.write("')::json")
        self.in_json = old_in_json

    def visit_IfExp(self, ifexp):
        self.buf.write("(CASE")
        while ifexp:
            self.buf.write(" WHEN ")
            self.visit(ifexp.test)
            self.buf.write(" THEN ")
            self.visit(ifexp.body)
            if isinstance(ifexp.orelse, ast.IfExp):
                ifexp = ifexp.orelse
            elif isinstance(ifexp.orelse, ast.AST):
                self.buf.write(" ELSE ")
                self.visit(ifexp.orelse)
                break
            else:
                ifexp = None

        self.buf.write(" END)")

    def visit_List(self, the_list):
        if self.in_json:
            self.buf.write("('[")
            first = True
            for elt in the_list.elts:
                if first:
                    first = False
                else:
                    self.buf.write(", ")
                self.buf.write(sql_as_json(elt))
            self.buf.write("]')")

        else:
            self.buf.write("ARRAY[")
            first = True
            for elt in the_list.elts:
                if first:
                    first = False
                else:
                    self.buf.write(", ")
                self.visit(elt)
            self.buf.write("]")

    def visit_Attribute(self, a):
        assert isinstance(a.value, ast.Name)
        name = a.value.id
        attr = a.attr

        if name == 'shape' and attr == 'type':
            self.buf.write("ST_GeomType(way)")
        elif name == 'meta' and attr == 'source':
            self.buf.write("\"meta_source\"")
        elif name == 'meta' and attr in ('ways', 'relations'):
            # we have no need to pass in ways or relations, as we can just
            # query the data from the planet_osm_ways/rels table. so this is
            # only needed to make the arguments list the right "shape".
            self.buf.write("NULL")
        else:
            raise RuntimeError("Unknown attribute pair (%r, %r)"
                               % (name, attr))

    def generic_visit(self, node):
        self.buf.write("<<<%s>>>" % type(node))

    def __str__(self):
        return self.buf.getvalue()


def sql_expression(expr, force_type=None):
    s = SQLExpression(force_type)
    s.visit(expr)
    return str(s)


class Case(ast.AST):

    def __init__(self, whens=[]):
        self.whens = whens


def merge_case(stmts):
    assigns = []
    whens = []
    for stmt in stmts:
        if isinstance(stmt, ast.Assign):
            assigns.append(stmt)
        elif (isinstance(stmt, ast.If) and
              len(stmt.orelse) == 0 and
              len(stmt.body) == 1 and
              isinstance(stmt.body[0], ast.Return)):
            whens.append(stmt)
        else:
            return stmts
    # all statements are ifs!
    return assigns + [Case(whens=whens)]


def assign_is_global(assign):
    assert len(assign.targets) == 1
    assert isinstance(assign.targets[0], ast.Name)
    # name type := expr
    name = assign.targets[0].id
    return name in GLOBALS


# The geometry type string returned by GeometryType is in all upper case, so
# we scan through the whole tree to rewrite rules where there's a shape.type
# on the LHS and a geometry type or tuple of geometry types on the RHS.
class GeomTypeTransformer(ast.NodeTransformer):

    def visit_Compare(self, cp):
        left = cp.left
        ops = cp.ops
        cmps = cp.comparators

        if isinstance(left, ast.Attribute) and \
           isinstance(left.value, ast.Name) and \
           left.value.id == 'shape' and \
           left.attr == 'type':
            call = ast.Call(
                ast.Name('ST_GeometryType', ast.Load()),
                [ast.Name('shape', ast.Load())],
                [], None, None)
            left = ast.copy_location(call, left)
            renamer = GeomNameTransformer()
            cmps = map(renamer.visit, cmps)

        return ast.copy_location(ast.Compare(left, ops, cmps), cp)


class GeomNameTransformer(ast.NodeTransformer):

    GEOM_TYPES = {
        'Point': 'ST_Point',
        'MultiPoint': 'ST_MultiPoint',
        'LineString': 'ST_LineString',
        'MultiLineString': 'ST_MultiLineString',
        'Polygon': 'ST_Polygon',
        'MultiPolygon': 'ST_MultiPolygon',
        'Line': 'ST_LineString',
        'MultiLine': 'ST_MultiLineString',
    }

    def visit_Str(self, s):
        val = self.GEOM_TYPES.get(s.s)
        if val:
            return ast.copy_location(ast.Str(val), s)
        return s


class SQLVisitor(ast.NodeVisitor):

    def __init__(self, io, force_type, return_type):
        self.io = io
        self.force_type = force_type
        self.return_type = return_type
        self.indent = 0

    def writeln(self, msg):
        self.io.write(" " * self.indent)
        self.io.write(msg)
        self.io.write("\n")

    def add_indent(self, n):
        self.indent += n

    def visit_FunctionDef(self, defn):
        self.writeln("CREATE OR REPLACE FUNCTION %s"
                     "(fid bigint, way geometry, tags hstore, way_area real,"
                     " meta_source text)"
                     % defn.name)
        self.writeln("RETURNS %s AS $$" % (self.return_type,))
        self.add_indent(2)
        seen_begin = False
        wrote_declare = False
        for stmt in merge_case(defn.body):
            if isinstance(stmt, ast.Assign):
                if assign_is_global(stmt):
                    continue
                if seen_begin:
                    raise RuntimeError(
                        "Assignment statement after function body begins.")
                if not wrote_declare:
                    self.add_indent(-2)
                    self.writeln("DECLARE")
                    self.add_indent(2)
                    wrote_declare = True
                self.visit(stmt)
            else:
                if not seen_begin:
                    seen_begin = True
                    self.add_indent(-2)
                    self.writeln("BEGIN")
                    self.add_indent(2)
                self.visit(stmt)
        self.add_indent(-2)
        self.writeln("END")
        self.writeln("$$ LANGUAGE plpgsql IMMUTABLE;")
        self.writeln("")
        self.writeln("")

    def visit_If(self, if_stmt):
        condition = sql_expression(if_stmt.test)
        self.writeln("IF (%s) THEN" % str(condition))
        self.add_indent(2)
        for stmt in if_stmt.body:
            self.visit(stmt)
        self.add_indent(-2)
        if if_stmt.orelse:
            self.writeln("ELSE")
            self.add_indent(2)
            for stmt in if_stmt.orelse:
                self.visit(stmt)
            self.add_indent(-2)
        self.writeln("ENDIF")

    def visit_Case(self, case):
        self.writeln("RETURN CASE")
        self.add_indent(2)
        for when in case.whens:
            self.writeln("WHEN %s" % sql_expression(when.test))
            self.add_indent(2)
            self.writeln("THEN %s" % sql_expression(when.body[0].value,
                                                    self.force_type))
            self.add_indent(-2)
        self.writeln("ELSE NULL")
        self.add_indent(-2)
        self.writeln("END;")

    def visit_Assign(self, assign):
        assert len(assign.targets) == 1
        assert isinstance(assign.targets[0], ast.Name)
        # name type := expr
        name = assign.targets[0].id
        # TODO: need to support variable types other than REAL?
        expr = sql_expression(assign.value, float)
        self.writeln("%s REAL := %s;" % (name, expr))

    def generic_visit(self, node):
        self.writeln("<<< don't yet understand what a %s is for... >>>"
                     % (type(node),))


def make_function_name_props(layer_name):
    return 'mz_calculate_json_%s_' % (layer_name,)


def make_function_name_min_zoom(layer_name):
    return 'mz_calculate_min_zoom_%s_' % (layer_name,)


def table_is_osm(name):
    return name.startswith('planet_osm_')


def table_is_polygonal(name):
    return name in POLYGON_TABLES


def calculate_meta_source_for_table(name):
    if table_is_osm(name) or name == 'admin_areas':
        return 'osm'
    elif name == 'contours':
        return 'vfp'
    elif name.startswith('ne_'):
        return 'ne'
    elif name.startswith('wof_'):
        return 'wof'
    elif name in ('buffered_land', 'land_polygons', 'water_polygons'):
        return 'shp'
    else:
        raise RuntimeError('Unknown table %r, cannot calculate meta source' %
                           (name,))


def print_adaptor(io, layer, table, calc, return_type):
    var = dict(layer=layer, table=table, calc=calc,
               return_type=return_type)

    if table_is_polygonal(table):
        var['way_area'] = 'row.way_area'
    else:
        var['way_area'] = '0::real'

    if table_is_osm(table):
        var['fid_column'] = 'osm_id'
        var['geom_column'] = 'way'
        var['tags_expr'] = 'row.tags'

    else:
        var['fid_column'] = 'gid'
        var['geom_column'] = 'the_geom'
        var['tags_expr'] = 'hstore(row)'

    var['meta_source'] = calculate_meta_source_for_table(table)

    io.write(ADAPTOR_QUERY % var)


def write_sql(io):
    from vectordatasource.meta import find_yaml_path

    yaml_path = find_yaml_path()
    for output_fn, make_fn_name, force_type, return_type in (
            (output_kind, make_function_name_props, None, 'JSON'),
            (output_min_zoom, make_function_name_min_zoom, float, 'REAL')):
        layer_result = parse_layers(yaml_path, output_fn, make_fn_name)
        assert isinstance(layer_result, LayerParseResult)
        for function_data in layer_result.layer_data:
            assert isinstance(function_data, FunctionData)
            ast_fn = function_data.ast
            ast_fn = GeomTypeTransformer().visit(ast_fn)
            visitor = SQLVisitor(io, force_type, return_type)
            visitor.visit(ast_fn)

    for layer, tables in LAYER_TABLES.items():
        for table in tables:
            for calc, return_type in [('json', 'JSON'), ('min_zoom', 'REAL')]:
                print_adaptor(io, layer, table, calc, return_type)


if __name__ == '__main__':
    write_sql(sys.stdout)
