def to_float(x):
    """
    attempts to convert x to a floating point value,
    first removing some common punctuation. returns
    None if conversion failed.
    """

    if x is None:
        return None
    # normalize punctuation
    x = x.replace(';', '.').replace(',', '.')
    try:
        return float(x)
    except ValueError:
        return None


def calculate_way_area(shape):
    result = 0
    if shape.type in ('MultiPolygon', 'Polygon'):
        result = shape.area
    return result


def get_height_from_props(props):
    height_str = props.get('height')
    if height_str:
        height = to_float(height_str)
        if height is not None:
            return height
    levels_str = props.get('levels')
    if levels_str:
        levels = to_float(levels_str)
        if levels is not None:
            result = max(levels, 1) * 3 + 2
            return result
    if height_str or levels_str:
        return 1e10


def calculate_volume(area, props):
    result = 0
    if area > 0:
        height = get_height_from_props(props)
        if height is not None and height > 0:
            result = area * height
    return result


def calculate_1px_zoom(way_area):
    import math
    # can't take logarithm of zero, and some ways have
    # incredibly tiny areas, down to even zero. also, by z16
    # all features really should be visible, so we clamp the
    # computation at the way area which would result in 16
    # being returned.
    if way_area < 5.704:
        return 16
    else:
        return 17.256 - math.log(way_area) / math.log(4)


def calculate_path_major_route(fid):
    # TODO: implement me! current implementation is a stub.
    return 18
