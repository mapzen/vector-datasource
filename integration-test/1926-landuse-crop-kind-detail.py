# -*- encoding: utf-8 -*-
from . import FixtureTest


class FarmlandCropTest(FixtureTest):

    def test_crop(self):
        import dsl

        z, x, y = (16, 10631, 25149)

        self.generate_fixtures(
            # https://www.openstreetmap.org/way/145660534
            dsl.way(145660534, dsl.tile_box(z, x, y), {
                'landuse': u'farmland',
                'crop': u'rice',
                'source': u'openstreetmap.org',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 145660534,
                'kind': 'farmland',
                'kind_detail': 'rice',
            })

    def test_crop_remap_sugarcane(self):
        import dsl

        z, x, y = (16, 10631, 25149)

        self.generate_fixtures(
            # https://www.openstreetmap.org/way/145660534
            dsl.way(145660534, dsl.tile_box(z, x, y), {
                'landuse': u'farmland',
                'crop': u'cana-de-a\u00e7\u00facar',
                'source': u'openstreetmap.org',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 145660534,
                'kind': 'farmland',
                'kind_detail': 'sugarcane',
            })
