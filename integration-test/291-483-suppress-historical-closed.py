## Best buy (closed)
# https://www.openstreetmap.org/way/241643507

# building should be present at z15
assert_has_feature(
    15, 5232, 12654, 'buildings',
    {'id': 241643507, 'kind': 'building', 'kind_detail': 'retail'})

# but POI shouldn't
assert_no_matching_feature(
    15, 5232, 12654, 'pois',
    {'id': 241643507})

# but POI should be present at z17 and marked as closed
assert_has_feature(
    17, 20931, 50616, 'pois',
    {'id': 241643507, 'kind': 'closed', 'min_zoom': 17})
