#!/usr/bin/env python3
"""
GBox 2D Animation Converter

5 interfaces, all support flexible input/output:
  - Input:  str (file path) or bytes/dict (data)
  - Output: with output param → write file, return path; without → return data
"""

import os
import sys
import json
import io
import tempfile

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))

from ani_parser import (
    parse_2dani_to_json,
    parse_2dani_to_json_with_embedded_images,
    create_2dani_from_json,
    create_2dani_from_image,
)
from ani_scale import (
    scale_animation,
    scale_animation_to_fit,
    calculate_aabb,
    translate_animation,
)


def _read_bytes(data):
    """Read data as bytes: str → read file, bytes → passthrough."""
    if isinstance(data, str):
        with open(data, 'rb') as f:
            return f.read()
    return data


def _write_output(result_bytes, output):
    """If output path given, write and return path. Otherwise return bytes."""
    if output:
        os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
        with open(output, 'wb') as f:
            f.write(result_bytes)
        return output
    return result_bytes


def _parse_with_images(raw_data, source=None):
    """
    Parse 2dani binary, extract images to temp dir, absolutize link_images.
    Returns (preview_path, json_data) with images preserved.
    """
    # We keep a temp dir alive by stashing it on the function (cleaned up on exit)
    tmp_dir = tempfile.mkdtemp(prefix='gbox_2dani_')
    _parse_with_images._tmps = getattr(_parse_with_images, '_tmps', [])
    _parse_with_images._tmps.append(tmp_dir)

    base_name = None
    if isinstance(source, str):
        base_name = os.path.splitext(os.path.basename(source))[0]
        if base_name.endswith('.2dani'):
            base_name = base_name[:-6]

    json_data = parse_2dani_to_json(raw_data, tmp_dir, base_name)

    # Absolutize link_images so create_2dani_from_json can find them
    preview_path = ""
    abs_images = []
    for img_name in json_data['animation'].get('link_images', []):
        full = os.path.join(tmp_dir, img_name)
        if os.path.exists(full):
            abs_images.append(full)
            if not preview_path:
                preview_path = full
        else:
            abs_images.append(img_name)
    json_data['animation']['link_images'] = abs_images

    return preview_path, json_data


# ── Interface 1: image → 2dani ──

def image_to_2dani(image, width, height, center_x=None, center_y=None,
                   embed=True, output=None):
    """
    Convert image to 2dani format.

    Args:
        image: str (file path) or bytes (image data)
        width, height: animation dimensions
        center_x, center_y: center point (default: center of dimensions)
        embed: embed image binary in 2dani (default True)
        output: str path → write file; None → return bytes
    """
    # If bytes input, write to temp file (ani_parser needs a file path)
    if isinstance(image, bytes):
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        try:
            tmp.write(image)
            tmp.close()
            result = create_2dani_from_image(tmp.name, width, height,
                                             center_x, center_y, embed_binary=embed)
        finally:
            os.unlink(tmp.name)
    else:
        result = create_2dani_from_image(image, width, height,
                                         center_x, center_y, embed_binary=embed)
    return _write_output(result, output)


# ── Interface 2: json → 2dani ──

def json_to_2dani(data, preview_image=None, embed=False, output=None):
    """
    Convert JSON animation data to 2dani format.

    Args:
        data: str (json file path) or dict (json data)
        preview_image: str (path) or bytes (image data) or None
        embed: embed linked images as binary
        output: str path → write file; None → return bytes
    """
    json_dir = ""
    if isinstance(data, str):
        json_dir = os.path.dirname(os.path.abspath(data))
        with open(data, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    else:
        json_data = data

    # Resolve relative link_images paths relative to JSON file directory
    if json_dir and embed:
        imgs = json_data['animation'].get('link_images', [])
        resolved = []
        for img_path in imgs:
            if not os.path.isabs(img_path) and not os.path.exists(img_path):
                candidate = os.path.join(json_dir, img_path)
                if os.path.exists(candidate):
                    img_path = candidate
            resolved.append(img_path)
        json_data['animation']['link_images'] = resolved

    # Handle preview image
    preview_path = ""
    tmp_preview = None
    if preview_image:
        if isinstance(preview_image, bytes):
            tmp_preview = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp_preview.write(preview_image)
            tmp_preview.close()
            preview_path = tmp_preview.name
        else:
            preview_path = preview_image

    try:
        result = create_2dani_from_json(json_data, preview_path, embed_binary=embed)
    finally:
        if tmp_preview:
            os.unlink(tmp_preview.name)

    return _write_output(result, output)


# ── Interface 3: 2dani → json ──

def parse_2dani(data, output_dir=None):
    """
    Parse 2dani to JSON.

    Args:
        data: str (2dani file path) or bytes (2dani data)
        output_dir: str → extract images to directory; None → embed as base64
    Returns:
        dict: JSON animation data
    """
    raw = _read_bytes(data)
    base_name = None
    if isinstance(data, str):
        base_name = os.path.splitext(os.path.basename(data))[0]
        if base_name.endswith('.2dani'):
            base_name = base_name[:-6]

    if output_dir:
        return parse_2dani_to_json(raw, output_dir, base_name)
    else:
        return parse_2dani_to_json_with_embedded_images(raw, base_name)


# ── Interface 4: scale 2dani ──

def scale_2dani(data, scale_factor, output=None):
    """
    Scale 2dani animation by a factor.

    Args:
        data: str (2dani file path) or bytes (2dani data)
        scale_factor: float scale factor
        output: str path → write file; None → return bytes
    """
    raw = _read_bytes(data)
    preview_path, json_data = _parse_with_images(raw, data)
    scaled = scale_animation(json_data, scale_factor)
    result = create_2dani_from_json(scaled, preview_image_path=preview_path,
                                    embed_binary=True)
    return _write_output(result, output)


# ── Interface 5: fit 2dani ──

def fit_2dani(data, width, height, center_x=None, center_y=None, output=None):
    """
    Scale 2dani animation to fit target dimensions, optionally re-center.

    Args:
        data: str (2dani file path) or bytes (2dani data)
        width, height: target dimensions
        center_x, center_y: new center point (None = keep original center)
        output: str path → write file; None → return bytes
    """
    raw = _read_bytes(data)
    preview_path, json_data = _parse_with_images(raw, data)
    fitted = scale_animation_to_fit(json_data, width, height)

    # Re-center if requested
    if center_x is not None or center_y is not None:
        min_x, min_y, max_x, max_y = calculate_aabb(fitted)
        cur_cx = (min_x + max_x) / 2
        cur_cy = (min_y + max_y) / 2
        target_cx = -center_x if center_x is not None else cur_cx
        target_cy = -center_y if center_y is not None else cur_cy
        dx = target_cx - cur_cx
        dy = target_cy - cur_cy
        fitted = translate_animation(fitted, dx, dy)

    result = create_2dani_from_json(fitted, preview_image_path=preview_path,
                                    embed_binary=True)
    return _write_output(result, output)


# ── CLI ──

def main():
    import argparse
    parser = argparse.ArgumentParser(description='GBox 2D Animation Converter')
    sub = parser.add_subparsers(dest='command')

    # image_to_2dani
    p = sub.add_parser('from_image', help='Convert image to 2dani')
    p.add_argument('input', help='Image file path')
    p.add_argument('output', help='Output 2dani file path')
    p.add_argument('--width', type=int, default=200)
    p.add_argument('--height', type=int, default=200)
    p.add_argument('--center-x', type=float)
    p.add_argument('--center-y', type=float)
    p.add_argument('--embed', action='store_true', default=True)

    # json_to_2dani
    p = sub.add_parser('from_json', help='Convert JSON to 2dani')
    p.add_argument('input', help='JSON file path')
    p.add_argument('output', help='Output 2dani file path')
    p.add_argument('--preview', help='Preview image path')
    p.add_argument('--embed', action='store_true')

    # parse_2dani
    p = sub.add_parser('to_json', help='Convert 2dani to JSON')
    p.add_argument('input', help='2dani file path')
    p.add_argument('output_dir', help='Output directory')
    p.add_argument('--base-name', default='animation')

    # scale_2dani
    p = sub.add_parser('scale', help='Scale 2dani by factor')
    p.add_argument('input', nargs='+', help='2dani file(s)')
    p.add_argument('--scale', type=float, required=True)
    p.add_argument('--output', help='Output file path')
    p.add_argument('--output-dir', help='Output directory')

    # fit_2dani
    p = sub.add_parser('fit', help='Fit 2dani to target size')
    p.add_argument('input', nargs='+', help='2dani file(s)')
    p.add_argument('--width', type=int, required=True)
    p.add_argument('--height', type=int, required=True)
    p.add_argument('--center-x', type=float)
    p.add_argument('--center-y', type=float)
    p.add_argument('--output', help='Output file path')
    p.add_argument('--output-dir', help='Output directory')

    args = parser.parse_args()

    if args.command == 'from_image':
        result = image_to_2dani(args.input, args.width, args.height,
                                args.center_x, args.center_y,
                                embed=args.embed, output=args.output)
        print(f"Created: {result} ({os.path.getsize(result)} bytes)")

    elif args.command == 'from_json':
        result = json_to_2dani(args.input, preview_image=args.preview,
                               embed=args.embed, output=args.output)
        print(f"Created: {result} ({os.path.getsize(result)} bytes)")

    elif args.command == 'to_json':
        result = parse_2dani(args.input, output_dir=args.output_dir)
        json_path = os.path.join(args.output_dir, f'{args.base_name}.json')
        os.makedirs(args.output_dir, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Created: {json_path}")
        print(f"  Name: {result['animation']['name']}")
        print(f"  Kinds: {len(result['animation']['kinds'])}")

    elif args.command == 'scale':
        for inp in args.input:
            out = args.output or (os.path.join(args.output_dir, os.path.basename(inp))
                                  if args.output_dir else inp)
            result = scale_2dani(inp, args.scale, output=out)
            print(f"Scaled: {inp} -> {result}")

    elif args.command == 'fit':
        for inp in args.input:
            out = args.output or (os.path.join(args.output_dir, os.path.basename(inp))
                                  if args.output_dir else inp)
            result = fit_2dani(inp, args.width, args.height,
                               args.center_x, args.center_y, output=out)
            print(f"Fitted: {inp} -> {result}")

    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
