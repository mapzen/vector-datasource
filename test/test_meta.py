# -*- coding: utf-8 -*-

import unittest


def memoize(f):
    result = {}

    def wrapped(*args, **kwargs):
        cache_key = tuple(args)
        if not result:
            result[cache_key] = f(*args, **kwargs)
        return result[cache_key]

    return wrapped


@memoize
def parse_layers_props(yaml_path):
    from vectordatasource.meta.python import parse_layers, output_kind, \
        make_function_name_props
    return parse_layers(yaml_path, output_kind, make_function_name_props)


@memoize
def parse_layers_min_zoom(yaml_path):
    from vectordatasource.meta.python import parse_layers, output_min_zoom, \
        make_function_name_min_zoom
    return parse_layers(
        yaml_path, output_min_zoom, make_function_name_min_zoom)


@memoize
def find_yaml_path():
    from vectordatasource.meta import find_yaml_path
    return find_yaml_path()


@memoize
def make_test_metadata():
    from tilequeue.process import make_metadata
    return make_metadata('test')


@memoize
def make_layer_data_props():
    yaml_path = find_yaml_path()
    layer_parse_result = parse_layers_props(yaml_path)
    by_name = {}
    for layer_datum in layer_parse_result.layer_data:
        by_name[layer_datum.layer] = layer_datum
    return layer_parse_result.layer_data, by_name


@memoize
def make_layer_data_min_zoom():
    yaml_path = find_yaml_path()
    layer_parse_result = parse_layers_min_zoom(yaml_path)
    by_name = {}
    for layer_datum in layer_parse_result.layer_data:
        by_name[layer_datum.layer] = layer_datum
    return layer_parse_result.layer_data, by_name


class CallFuncTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()

    def test_layer_data_count(self):
        self.assertEquals(9, len(self.layer_data))

    def test_layer_names(self):
        exp_layers = set(('landuse', 'pois', 'transit', 'water', 'places',
                          'boundaries', 'buildings', 'roads', 'earth'))
        self.assertEquals(exp_layers, set(self.by_name.keys()))

    def test_layers_called_empty_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Point((0, 0))
        props = {}
        fid = 42
        meta = make_test_metadata()

        for layer_datum in self.layer_data:
            fn = layer_datum.fn
            result = fn(shape, props, fid, meta)
            self.assertTrue(isinstance(result, (dict, None.__class__)))


class BuildingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.buildings = cls.by_name['buildings']

    def test_building_basic(self):
        import shapely.geometry
        shape = shapely.geometry.Point((0, 0))
        props = dict(building='yes')
        fid = 42
        meta = make_test_metadata()
        out_props = self.buildings.fn(shape, props, fid, meta)
        self.assertEquals('building', out_props.get('kind'))
        self.assertIsNone(out_props.get('kind_detail'))

    def test_building_kind_detail(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (1, 1), (1, 0)])
        props = {
            'building': 'beach_hut',
            'building:part': 'passageway',
        }
        fid = 42
        meta = make_test_metadata()
        out_props = self.buildings.fn(shape, props, fid, meta)
        self.assertEquals('building', out_props.get('kind'))
        self.assertEquals('beach_hut', out_props.get('kind_detail'))
        self.assertEquals('passageway', out_props.get('building_part'))


class BoundariesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.boundaries = cls.by_name['boundaries']

    def test_osm(self):
        props = {
            'boundary': 'administrative',
            'boundary:type': 'aboriginal_lands',
            'admin_level': '2',
        }
        meta = make_test_metadata()
        out_props = self.boundaries.fn(None, props, None, meta)
        self.assertEquals('aboriginal_lands', out_props.get('kind'))
        self.assertEquals('2', out_props.get('kind_detail'))

    def test_ne(self):
        props = {
            'featurecla': 'Admin-1 region boundary',
        }
        meta = make_test_metadata()
        out_props = self.boundaries.fn(None, props, None, meta)
        self.assertEquals('macroregion', out_props.get('kind'))
        self.assertEquals('3', out_props.get('kind_detail'))


class EarthTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.earth = cls.by_name['earth']

    def test_osm(self):
        props = {
            'natural': 'arete',
        }
        meta = make_test_metadata()
        out_props = self.earth.fn(None, props, None, meta)
        self.assertEquals('arete', out_props.get('kind'))

    def test_ne(self):
        props = {
            'gid': 42,
        }
        # this rule depends on a particular source being set
        from tilequeue.process import make_metadata
        meta = make_metadata('ne')
        out_props = self.earth.fn(None, props, None, meta)
        self.assertEquals('earth', out_props.get('kind'))


class LanduseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.landuse = cls.by_name['landuse']

    def test_osm(self):
        props = {
            'natural': 'scree',
        }
        meta = make_test_metadata()
        out_props = self.landuse.fn(None, props, None, meta)
        self.assertEquals('scree', out_props.get('kind'))


class PlacesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.places = cls.by_name['places']

    def test_osm(self):
        props = {
            'name': 'foo',
            'place': 'isolated_dwelling',
        }
        meta = make_test_metadata()
        out_props = self.places.fn(None, props, None, meta)
        self.assertEquals('locality', out_props.get('kind'))
        self.assertEquals('isolated_dwelling', out_props.get('kind_detail'))

    def test_ne(self):
        props = {
            'scalerank': 42,
            'featurecla': 'Scientific station',
        }
        meta = make_test_metadata()
        out_props = self.places.fn(None, props, None, meta)
        self.assertEquals('locality', out_props.get('kind'))
        self.assertEquals('scientific_station', out_props.get('kind_detail'))


class PoisTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.pois = cls.by_name['pois']

    def test_disused(self):
        props = dict(disused='yes')
        meta = make_test_metadata()
        out_props = self.pois.fn(None, props, None, meta)
        self.assertIsNone(out_props.get('kind'))

        props = dict(disused='no', name='foo', leisure='playground')
        out_props = self.pois.fn(None, props, None, meta)
        self.assertEquals('playground', out_props.get('kind'))

    def test_no_name_ok(self):
        props = dict(historic='landmark')
        meta = make_test_metadata()
        out_props = self.pois.fn(None, props, None, meta)
        self.assertEquals('landmark', out_props.get('kind'))

    def test_no_name_none(self):
        props = dict(tourism='aquarium')
        meta = make_test_metadata()
        out_props = self.pois.fn(None, props, None, meta)
        self.assertIsNone(out_props.get('kind'))


class RoadsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.roads = cls.by_name['roads']

    def test_osm(self):
        props = {
            'name': 'foo',
            'highway': 'motorway',
        }
        meta = make_test_metadata()
        out_props = self.roads.fn(None, props, None, meta)
        self.assertEquals('highway', out_props.get('kind'))
        self.assertEquals('motorway', out_props.get('kind_detail'))

    def test_ne(self):
        props = {
            'featurecla': 'Road',
            'type': 'Road',
            'scalerank': 42,
        }
        meta = make_test_metadata()
        out_props = self.roads.fn(None, props, None, meta)
        self.assertEquals('major_road', out_props.get('kind'))
        self.assertEquals('secondary', out_props.get('kind_detail'))


class TransitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.transit = cls.by_name['transit']

    def test_osm(self):
        props = {
            'route': 'subway',
        }
        meta = make_test_metadata()
        out_props = self.transit.fn(None, props, None, meta)
        self.assertEquals('subway', out_props.get('kind'))


class WaterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_props()
        cls.water = cls.by_name['water']

    def test_osm(self):
        props = dict(waterway='riverbank')
        meta = make_test_metadata()
        out_props = self.water.fn(None, props, None, meta)
        self.assertEquals('riverbank', out_props.get('kind'))

        props = dict(waterway='riverbank', intermittent='yes')
        out_props = self.water.fn(None, props, None, meta)
        self.assertEquals('riverbank', out_props.get('kind'))
        self.assertTrue(out_props.get('intermittent'))

    def test_ne(self):
        props = dict(featurecla='Lake')
        meta = make_test_metadata()
        out_props = self.water.fn(None, props, None, meta)
        self.assertEquals('lake', out_props.get('kind'))


class LanduseMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.landuse = cls.by_name['landuse']

    def test_small_zoo(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (1, 1), (1, 0)])
        props = {
            'zoo': 'enclosure',
        }
        meta = make_test_metadata()
        out_min_zoom = self.landuse.fn(shape, props, None, meta)
        self.assertEquals(16, out_min_zoom)

    def test_large_zoo(self):
        import shapely.geometry
        s = 100000
        shape = shapely.geometry.Polygon([(0, 0), (s, s), (s, 0)])
        props = {
            'zoo': 'enclosure',
        }
        meta = make_test_metadata()
        out_min_zoom = self.landuse.fn(shape, props, None, meta)
        self.assertEquals(9, out_min_zoom)

    def test_medium_zoo(self):
        import shapely.geometry
        from vectordatasource.util import calculate_way_area, \
            calculate_1px_zoom
        import math

        target_zoom = 11.0
        # want a zoom 11 feature, so make one with a triangle.
        target_area = math.exp((17.256 - target_zoom) * math.log(4))
        # make area with a half-square triangle.
        s = math.sqrt(target_area * 2.0)
        shape = shapely.geometry.Polygon([(0, 0), (s, s), (s, 0)])
        props = {
            'zoo': 'enclosure',
        }

        # test the utility functions we're relying on
        util_way_area = calculate_way_area(shape)
        self.assertAlmostEqual(target_area, util_way_area)
        util_min_zoom = calculate_1px_zoom(shape.area)
        self.assertAlmostEqual(target_zoom, util_min_zoom)

        meta = make_test_metadata()
        out_min_zoom = self.landuse.fn(shape, props, None, meta)
        self.assertAlmostEqual(target_zoom, out_min_zoom)


class BoundariesMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.boundaries = cls.by_name['boundaries']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.LineString([(0, 0), (1, 1), (1, 0)])
        props = {
            'boundary': 'administrative',
            'admin_level': '2',
        }
        meta = make_test_metadata()
        out_min_zoom = self.boundaries.fn(shape, props, None, meta)
        self.assertEquals(8, out_min_zoom)


class BuildingsMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.buildings = cls.by_name['buildings']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
        props = {
            'building': 'yes',
        }
        meta = make_test_metadata()
        out_min_zoom = self.buildings.fn(shape, props, None, meta)
        self.assertEquals(17, out_min_zoom)


class EarthMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.earth = cls.by_name['earth']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (1, 1), (1, 0)])
        props = {
            'place': 'island',
            'name': 'An Island',
        }
        meta = make_test_metadata()
        out_min_zoom = self.earth.fn(shape, props, None, meta)
        self.assertEquals(15, out_min_zoom)


class PlacesMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.places = cls.by_name['places']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Point(0, 0)
        props = {
            'place': 'country',
            'name': 'A Country',
        }
        meta = make_test_metadata()
        out_min_zoom = self.places.fn(shape, props, None, meta)
        self.assertEquals(2, out_min_zoom)


class PoisMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.pois = cls.by_name['pois']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (1, 1), (1, 0)])
        props = {
            'boundary': 'national_park',
            'operator': 'US Forest Service',
            'name': 'A Forest',
        }
        meta = make_test_metadata()
        out_min_zoom = self.pois.fn(shape, props, None, meta)
        self.assertEquals(14, out_min_zoom)


class RoadsMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.roads = cls.by_name['roads']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.LineString([(0, 0), (1, 1), (1, 0)])
        props = {
            'highway': 'service',
        }
        meta = make_test_metadata()
        out_min_zoom = self.roads.fn(shape, props, None, meta)
        self.assertEquals(14, out_min_zoom)


class TransitMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.transit = cls.by_name['transit']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.LineString([(0, 0), (1, 1), (1, 0)])
        props = {
            'route': 'train',
            'service': 'high_speed',
        }
        meta = make_test_metadata()
        out_min_zoom = self.transit.fn(shape, props, None, meta)
        self.assertEquals(5, out_min_zoom)


class WaterMinZoomTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layer_data, cls.by_name = make_layer_data_min_zoom()
        cls.water = cls.by_name['water']

    def test_feature(self):
        import shapely.geometry
        shape = shapely.geometry.Polygon([(0, 0), (1, 1), (1, 0)])
        props = {
            'leisure': 'swimming_pool',
        }
        meta = make_test_metadata()
        out_min_zoom = self.water.fn(shape, props, None, meta)
        self.assertEquals(16, out_min_zoom)


class RoundTripRuleTest(unittest.TestCase):

    def test_not_rule_roundtrip_through_astformatter(self):
        yaml_data = dict(
            filters=[dict(
                filter={
                    'foo': 'bar',
                    'not': {
                        'any': [
                            dict(baz='quux'),
                            dict(fleem='morx'),
                        ]
                    }
                },
                min_zoom=7,
                output=dict(kind='triggered')
            )],
        )
        from vectordatasource.meta.python import make_empty_ast_state
        from vectordatasource.meta.python import output_kind
        from vectordatasource.meta.python import make_function_name_props
        from vectordatasource.meta.python import parse_layer_from_yaml
        ast_state = make_empty_ast_state()
        ast_fn = parse_layer_from_yaml(
            ast_state, yaml_data, 'fn_name', output_kind,
            make_function_name_props)

        # first check that if we compile the function from the ast, we
        # get an expected result
        import ast
        mod = ast.Module([ast_fn])
        mod_with_linenos = ast.fix_missing_locations(mod)
        code = compile(mod_with_linenos, '<string>', 'exec')
        scope = {}
        exec code in scope
        fn = scope['fn_name_props']

        shape = None
        props = dict(some='value')
        fid = 42
        meta = make_test_metadata()
        result = fn(shape, props, fid, meta)
        self.assertIsNone(result)

        # now, round trip it through the ast formatter
        # and see if we get the same result
        import astformatter
        formatter = astformatter.ASTFormatter()
        code_str = formatter.format(ast_fn, mode='exec')

        mod = ast.parse(code_str)
        mod_with_linenos = ast.fix_missing_locations(mod)
        code = compile(mod_with_linenos, '<string>', 'exec')
        scope = {}
        exec code in scope
        fn = scope['fn_name_props']

        result = fn(shape, props, fid, meta)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
