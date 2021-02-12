# -*- encoding: utf-8 -*-
from . import FixtureTest


class DemoteEarlyLandcover(FixtureTest):

    def test_forest(self):
        import dsl

        z, x, y = (9, 123, 180)

        self.generate_fixtures(
            # https://www.openstreetmap.org/relation/1430156
            dsl.way(1430156, dsl.box_area(z, x, y, 2068410835), {
                'landuse': 'forest',
                'name': 'Savanna State Forest',
                'source': 'openstreetmap.org',
                'type': 'multipolygon',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 1430156,
                'kind': 'forest',
                'min_zoom': 9,
            })

    def test_natural_wood_usfs_1(self):
        # previously, being operator=USFS had meant a zoom bump, but no longer.
        import dsl

        z, x, y = (14, 2733, 6235)

        self.generate_fixtures(
            # https://www.openstreetmap.org/relation/7339333
            dsl.way(7339333, dsl.box_area(z, x, y, 16961064), {
                'access': 'yes',
                'natural': 'wood',
                'operator': 'United States Forest Service',
                'source': 'openstreetmap.org',
                'type': 'multipolygon',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 7339333,
                'kind': 'natural_wood',
                'min_zoom': 9,
            })

    def test_natural_wood_usfs_2(self):
        # previously, being operator=USFS had meant a zoom bump, but no longer.
        import dsl

        z, x, y = (14, 2734, 6245)

        self.generate_fixtures(
            # https://www.openstreetmap.org/relation/7352119
            dsl.way(7352119, dsl.box_area(z, x, y, 19525176), {
                'access': 'yes',
                'natural': 'wood',
                'operator': 'United States Forest Service',
                'source': 'openstreetmap.org',
                'type': 'multipolygon',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 7352119,
                'kind': 'natural_wood',
                'min_zoom': 9,
            })

    def test_natural_wood(self):
        import dsl

        z, x, y = (14, 11782, 7469)

        self.generate_fixtures(
            # https://www.openstreetmap.org/relation/5617154
            dsl.way(5617154, dsl.box_area(z, x, y, 9186148530), {
                'name': 'Nallamala Forest',
                'natural': 'wood',
                'source': 'openstreetmap.org',
                'type': 'multipolygon',
                'wikidata': 'Q1579454',
                'wikipedia': 'en:Nallamala Hills',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 5617154,
                'kind': 'natural_wood',
                'min_zoom': 9,
            })

    def test_residential(self):
        # having looked at this area on aerial imagery, it's a bit of a
        # stretch to call it "residential". there are houses, but they're
        # not exactly tightly packed. the population of allegedly 100,000
        # seems unrealistic. still, it serves as an example of the kind of
        # data that's out there.
        import dsl

        z, x, y = (14, 4478, 6953)

        self.generate_fixtures(
            # https://www.openstreetmap.org/relation/6612640
            dsl.way(6612640, dsl.box_area(z, x, y, 320463090), {
                'addr:state': 'Florida',
                'landuse': 'residential',
                'name': 'Golden Gate Estates',
                'population': '100000',
                'source': 'openstreetmap.org',
                'type': 'multipolygon',
            }),
        )

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 6612640,
                'kind': 'residential',
                'min_zoom': 10,
            })

    def _check_min_zoom(self, tags, kind, min_zoom, tile_zoom=14):
        import dsl

        z, x, y = (tile_zoom, 0, 0)

        shape = dsl.tile_box(min_zoom, 0, 0)
        all_tags = tags.copy()
        all_tags['source'] = 'openstreetmap.org'

        self.generate_fixtures(dsl.way(1, shape, all_tags))

        self.assert_has_feature(
            z, x, y, 'landuse', {
                'id': 1,
                'kind': kind,
                'min_zoom': min_zoom,
            })

    ######################################################################
    #
    # zoom 11+
    #
    ######################################################################

    def test_dam(self):
        self._check_min_zoom({'waterway': 'dam'}, 'dam', 11)

    def test_prison(self):
        self._check_min_zoom({'amenity': 'prison'}, 'prison', 11)

    def test_fort(self):
        self._check_min_zoom({'historic': 'fort'}, 'fort', 11)

    def test_range(self):
        self._check_min_zoom({'military': 'range'}, 'range', 11)

    def test_danger_area(self):
        self._check_min_zoom({'military': 'danger_area'}, 'danger_area', 11)

    ######################################################################
    #
    # zoom 12+
    #
    ######################################################################

    def test_sports_cente(self):
        self._check_min_zoom({'leisure': 'sports_centre'}, 'sports_centre', 12)

    def test_recreation_ground(self):
        self._check_min_zoom(
            {'landuse': 'recreation_ground'}, 'recreation_ground', 12)

    def test_recreation_track(self):
        self._check_min_zoom({'leisure': 'track'}, 'recreation_track', 12)

    def test_wastewater_plant(self):
        self._check_min_zoom(
            {'man_made': 'wastewater_plant'}, 'wastewater_plant', 12)

    def test_caravan_site(self):
        self._check_min_zoom({'tourism': 'caravan_site'}, 'caravan_site', 12)

    def test_camp_site(self):
        self._check_min_zoom({'tourism': 'camp_site'}, 'camp_site', 12)

    def test_aquarium(self):
        self._check_min_zoom({'tourism': 'aquarium'}, 'aquarium', 12)

    ######################################################################
    #
    # zoom 13+
    #
    ######################################################################

    def test_petting_zoo(self):
        self._check_min_zoom({'zoo': 'petting_zoo'}, 'petting_zoo', 13)

    def test_playground(self):
        self._check_min_zoom({'leisure': 'playground'}, 'playground', 13)

    def test_substation(self):
        self._check_min_zoom({'power': 'substation'}, 'substation', 13)

    def test_allotments(self):
        self._check_min_zoom({'landuse': 'allotments'}, 'allotments', 13)

    def test_pedestrian(self):
        self._check_min_zoom({'highway': 'pedestrian'}, 'pedestrian', 13)

    def test_fuel(self):
        self._check_min_zoom({'amenity': 'fuel'}, 'fuel', 13)

    def test_bridge(self):
        self._check_min_zoom({'man_made': 'bridge'}, 'bridge', 13)

    def test_footway(self):
        self._check_min_zoom({'highway': 'footway'}, 'footway', 13)

    def test_tower(self):
        self._check_min_zoom({'man_made': 'tower'}, 'tower', 13)

    def test_apron(self):
        self._check_min_zoom({'aeroway': 'apron'}, 'apron', 13)

    def test_hedge(self):
        self._check_min_zoom({'barrier': 'hedge'}, 'hedge', 13)

    def test_library(self):
        self._check_min_zoom({'amenity': 'library'}, 'library', 13)

    def test_theatre(self):
        self._check_min_zoom({'amenity': 'theatre'}, 'theatre', 13)

    def test_breakwater(self):
        self._check_min_zoom({'man_made': 'breakwater'}, 'breakwater', 13)

    def test_picnic_site(self):
        self._check_min_zoom({'tourism': 'picnic_site'}, 'picnic_site', 13)

    def test_dog_park(self):
        self._check_min_zoom({'leisure': 'dog_park'}, 'dog_park', 13)

    def test_cinema(self):
        self._check_min_zoom({'amenity': 'cinema'}, 'cinema', 13)

    def test_water_park(self):
        self._check_min_zoom({'leisure': 'water_park'}, 'water_park', 13)

    def test_harbour(self):
        self._check_min_zoom({'landuse': 'harbour'}, 'harbour', 13)

    def test_groyne(self):
        self._check_min_zoom({'man_made': 'groyne'}, 'groyne', 13)

    def test_runway(self):
        self._check_min_zoom({'aeroway': 'runway'}, 'runway', 13)

    def test_tree_row(self):
        self._check_min_zoom({'natural': 'tree_row'}, 'tree_row', 13)

    def test_animal(self):
        self._check_min_zoom({'attraction': 'animal'}, 'animal', 13)

    def test_taxiway(self):
        self._check_min_zoom({'aeroway': 'taxiway'}, 'taxiway', 13)

    def test_enclosure(self):
        self._check_min_zoom({'zoo': 'enclosure'}, 'enclosure', 13)

    def test_cutline(self):
        self._check_min_zoom({'man_made': 'cutline'}, 'cutline', 13)

    def test_trail_riding_station(self):
        self._check_min_zoom({'tourism': 'trail_riding_station'},
                             'trail_riding_station', 13)

    def test_aviary(self):
        self._check_min_zoom({'zoo': 'aviary'}, 'aviary', 13)

    def test_dyke(self):
        self._check_min_zoom({'man_made': 'dyke'}, 'dyke', 13)

    def test_summer_toboggan(self):
        self._check_min_zoom({'attraction': 'summer_toboggan'},
                             'summer_toboggan', 13)

    def test_winery(self):
        self._check_min_zoom({'tourism': 'winery'}, 'winery', 13)

    ######################################################################
    #
    # zoom 15+
    #
    ######################################################################

    def test_amusement_ride(self):
        self._check_min_zoom({'attraction': 'amusement_ride'},
                             'amusement_ride', 15, tile_zoom=15)

    def test_carousel(self):
        self._check_min_zoom({'attraction': 'carousel'}, 'carousel', 15,
                             tile_zoom=15)

    def test_water_slide(self):
        self._check_min_zoom({'attraction': 'water_slide'}, 'water_slide', 15,
                             tile_zoom=15)

    def test_roller_coaster(self):
        self._check_min_zoom({'attraction': 'roller_coaster'},
                             'roller_coaster', 15, tile_zoom=15)
