# sort functions to apply to features


def _sort_features_by_key(features, key):
    features.sort(key=key)
    return features


def _by_feature_property(property_name):
    def _feature_sort_by_property(feature):
        wkb, properties, fid = feature
        return properties.get(property_name)
    return _feature_sort_by_property


_by_feature_id = _by_feature_property('id')


def _by_area(feature):
    wkb, properties, fid = feature
    default_value = -1000
    sort_key = properties.get('area', default_value)
    return sort_key


def _sort_by_area_then_id(features):
    features.sort(key=_by_feature_id)
    features.sort(key=_by_area, reverse=True)
    return features


def _by_population(feature):
    wkb, properties, fid = feature
    default_value = -1000
    # depends on a transform run to convert population to an integer
    population = properties.get('population')
    return default_value if population is None else population


def _by_transit_score(feature):
    wkb, props, fid = feature
    return props.get('mz_transit_score', 0)


def _by_peak_elevation(feature):
    wkb, props, fid = feature
    kind = props.get('kind')
    if kind != 'peak' and kind != 'volcano':
        return 0
    return props.get('elevation', 0)


def _sort_by_transit_score_then_elevation_then_feature_id(features):
    features.sort(key=_by_feature_id)
    features.sort(key=_by_peak_elevation, reverse=True)
    features.sort(key=_by_transit_score, reverse=True)
    return features


def buildings(features, zoom):
    return _sort_by_area_then_id(features)


def earth(features, zoom):
    return _sort_features_by_key(features, _by_feature_id)


def landuse(features, zoom):
    return _sort_by_area_then_id(features)


def _place_key_desc(feature):
    sort_key = _by_population(feature), _by_area(feature)
    return sort_key


def places(features, zoom):
    features.sort(key=_place_key_desc, reverse=True)
    features.sort(key=_by_feature_property('mz_n_photos'), reverse=True)
    features.sort(key=_by_feature_property('min_zoom'))
    return features


def pois(features, zoom):
    return _sort_by_transit_score_then_elevation_then_feature_id(features)


def roads(features, zoom):
    return _sort_features_by_key(features, _by_feature_property('sort_rank'))


def water(features, zoom):
    return _sort_by_area_then_id(features)


def transit(features, zoom):
    return _sort_features_by_key(features, _by_feature_id)


def contours(features, zoom):
    return _sort_by_area_then_id(features)
