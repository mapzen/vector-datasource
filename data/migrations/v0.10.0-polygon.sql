UPDATE planet_osm_polygon
SET mz_poi_min_zoom = mz_calculate_min_zoom_pois(planet_osm_polygon.*)
WHERE
  amenity IN ('boat_rental', 'ranger_station', 'boat_storage') OR
  leisure IN ('water_park', 'beach_resort', 'summer_camp', 'dog_park', 'track', 'fishing', 'swimming_area', 'firepit') OR 
  historic IN ('battlefield', 'fort', 'monument') OR
  tourism IN ('caravan_site', 'picnic_site' ) OR 
  waterway IN ('dam') OR
  shop IN ('boat_rental', 'fishing', 'hunting', 'outdoor', 'scuba_diving', 'gas', 'motorcycle') OR
  tags->'rental' = 'boat' OR
  (shop = 'boat' AND tags->'rental' = 'yes') OR
  man_made IN ('beacon', 'cross', 'mineshaft', 'adit', 'water_well', 'communications_tower', 'observatory', 'telescope', 'offshore_platform', 'water_tower', 'mast') OR
  "natural" IN ('saddle', 'dune', 'geyser', 'sinkhole', 'hot_spring', 'rock', 'stone', 'waterfall') OR
  highway = 'trailhead' OR
  waterway = 'waterfall' OR
  tags->'whitewater' IN ('put_in;egress', 'put_in', 'egress', 'hazard', 'rapid');

UPDATE planet_osm_polygon
SET mz_water_min_zoom = mz_calculate_min_zoom_water(planet_osm_polygon.*)
WHERE mz_calculate_min_zoom_water(planet_osm_polygon.*) IS NOT NULL;

UPDATE planet_osm_polygon
SET mz_landuse_min_zoom = mz_calculate_min_zoom_landuse(planet_osm_polygon.*)
WHERE
  "natural" IN ('scree', 'stone', 'rock') OR
  leisure IN ('water_park', 'dog_park', 'track') OR
  historic IN ('battlefield', 'fort') OR
  tourism IN ('caravan_site', 'picnic_site') OR
  waterway IN ('dam');

UPDATE planet_osm_polygon
  SET mz_boundary_min_zoom = mz_calculate_min_zoom_boundaries(planet_osm_polygon.*)
  WHERE mz_calculate_min_zoom_boundaries(planet_osm_polygon.*) IS NOT NULL;

UPDATE planet_osm_polygon
  SET mz_building_min_zoom = mz_calculate_min_zoom_buildings(planet_osm_polygon.*)
  WHERE mz_calculate_min_zoom_buildings(planet_osm_polygon.*) IS NOT NULL;

CREATE INDEX new_planet_osm_polygon_water_geom_9_index ON planet_osm_polygon USING gist(way) WHERE mz_water_min_zoom <= 9;
CREATE INDEX new_planet_osm_polygon_water_geom_12_index ON planet_osm_polygon USING gist(way) WHERE mz_water_min_zoom <= 12;
CREATE INDEX new_planet_osm_polygon_water_geom_15_index ON planet_osm_polygon USING gist(way) WHERE mz_water_min_zoom <= 15;

CREATE INDEX new_planet_osm_polygon_boundary_geom_9_index ON planet_osm_polygon USING gist(way) WHERE mz_boundary_min_zoom <= 9;
CREATE INDEX new_planet_osm_polygon_boundary_geom_12_index ON planet_osm_polygon USING gist(way) WHERE mz_boundary_min_zoom <= 12;
CREATE INDEX new_planet_osm_polygon_boundary_geom_15_index ON planet_osm_polygon USING gist(way) WHERE mz_boundary_min_zoom <= 15;

CREATE INDEX new_planet_osm_polygon_building_geom_15_index ON planet_osm_polygon USING gist(way) WHERE mz_building_min_zoom <= 15;

BEGIN;
  DROP INDEX IF EXISTS planet_osm_polygon_water_geom_9_index;
  DROP INDEX IF EXISTS planet_osm_polygon_water_geom_12_index;
  DROP INDEX IF EXISTS planet_osm_polygon_water_geom_15_index;

  ALTER INDEX new_planet_osm_polygon_water_geom_9_index RENAME TO planet_osm_polygon_water_geom_9_index;
  ALTER INDEX new_planet_osm_polygon_water_geom_12_index RENAME TO planet_osm_polygon_water_geom_12_index;
  ALTER INDEX new_planet_osm_polygon_water_geom_15_index RENAME TO planet_osm_polygon_water_geom_15_index;

  DROP INDEX IF EXISTS planet_osm_polygon_boundary_geom_9_index;
  DROP INDEX IF EXISTS planet_osm_polygon_boundary_geom_12_index;
  DROP INDEX IF EXISTS planet_osm_polygon_boundary_geom_15_index;

  ALTER INDEX new_planet_osm_polygon_boundary_geom_9_index RENAME TO planet_osm_polygon_boundary_geom_9_index;
  ALTER INDEX new_planet_osm_polygon_boundary_geom_12_index RENAME TO planet_osm_polygon_boundary_geom_12_index;
  ALTER INDEX new_planet_osm_polygon_boundary_geom_15_index RENAME TO planet_osm_polygon_boundary_geom_15_index;

  DROP INDEX IF EXISTS planet_osm_polygon_building_geom_15_index;

  ALTER INDEX new_planet_osm_polygon_building_geom_15_index RENAME TO planet_osm_polygon_building_geom_15_index;
COMMIT;
