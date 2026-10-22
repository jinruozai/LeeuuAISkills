"""GBox 2D animation scaling utilities."""


def scale_animation(animation_data, scale_factor):
    """Scale all vertex positions by a uniform factor around origin."""
    for kind in animation_data['animation'].get('kinds', []):
        for track in kind.get('tracks', []):
            for key_frame in track.get('key_frames', []):
                for vertex in key_frame.get('vertices', []):
                    pos = vertex.get('position', [0, 0, 0])
                    vertex['position'] = [p * scale_factor for p in pos]
    return animation_data


def calculate_aabb(animation_data):
    """Calculate AABB of first kind. Returns (min_x, min_y, max_x, max_y)."""
    kinds = animation_data['animation'].get('kinds', [])
    if not kinds:
        return (0, 0, 0, 0)

    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for track in kinds[0].get('tracks', []):
        for key_frame in track.get('key_frames', []):
            for vertex in key_frame.get('vertices', []):
                x, y = vertex.get('position', [0, 0, 0])[:2]
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)

    if min_x == float('inf'):
        return (0, 0, 0, 0)
    return (min_x, min_y, max_x, max_y)


def scale_animation_to_fit(animation_data, target_width, target_height):
    """Scale animation to fit target dimensions (maintain aspect ratio)."""
    min_x, min_y, max_x, max_y = calculate_aabb(animation_data)
    cur_w = max_x - min_x
    cur_h = max_y - min_y

    if cur_w == 0 or cur_h == 0:
        return animation_data

    scale_factor = min(target_width / cur_w, target_height / cur_h)
    return scale_animation(animation_data, scale_factor)


def translate_animation(animation_data, dx, dy):
    """Translate all vertex positions by (dx, dy)."""
    for kind in animation_data['animation'].get('kinds', []):
        for track in kind.get('tracks', []):
            for key_frame in track.get('key_frames', []):
                for vertex in key_frame.get('vertices', []):
                    pos = vertex.get('position', [0, 0, 0])
                    vertex['position'] = [pos[0] + dx, pos[1] + dy, pos[2]]
    return animation_data
