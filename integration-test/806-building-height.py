from . import FixtureTest


class BuildingHeight(FixtureTest):
    def test_from_building_levels(self):
        # check that we synthesize a height value from building:levels
        # Way: R5 Tower A (431358377)
        self.load_fixtures(['https://www.openstreetmap.org/way/431358377'])

        self.assert_has_feature(
            16, 55897, 25449, 'buildings',
            {'id': 431358377, 'height': 77.0, 'kind': 'building',
             'building:levels': type(None), 'building_levels': type(None)})

    def test_min_height_from_min_levels(self):
        self.load_fixtures(['http://www.openstreetmap.org/way/336433763'])

        self.assert_has_feature(
            16, 19086, 24821, 'buildings',
            {'id': 336433763, 'min_height': 3.0, 'kind': 'building_part',
             'building_part': type(None), 'building:min_levels': type(None),
             'building_min_levels': type(None)})
