"""GBox 2D animation binary format parser and serializer."""

import os
import io
import re
import struct
from PIL import Image
from image_format_parser import detect_image_format, parse_image_data

# Constants
ANIFILE_FLAG = 0xB65EB0B0
ANIFILE_VER = 2
STR_2danidata = 0x519C4E66
STR_2danikind = 0x5E74D596
STR_2danitrack = 0xF53FF3EB
W_COLOR = 0xFFFFFFFF


# ── GBox string encoding ──

def write_gbox_unicode(s):
    """Encode string in GBox Unicode format (ASCII single-byte, non-ASCII as 0x80+count+UTF-16LE)."""
    encoded = bytearray()
    i = 0
    while i < len(s):
        cp = ord(s[i])
        if cp < 0x80:
            encoded.append(cp)
            i += 1
        else:
            j = i
            while j < len(s) and ord(s[j]) >= 0x80:
                j += 1
            count = j - i
            encoded.append(0x80 + count)
            for k in range(i, j):
                encoded.extend(struct.pack('<H', ord(s[k])))
            i = j
    encoded.append(0)  # null terminator
    return encoded


def write_auto_str(s):
    if not s:
        return b'\x00'
    encoded = write_gbox_unicode(s)
    length = len(encoded)
    if length < 0xFF:
        return struct.pack('<B', length) + encoded
    return b'\xFF' + struct.pack('<I', length) + encoded


def write_auto_var(var_data):
    if not var_data:
        return struct.pack('<I', 0)
    return struct.pack('<I', len(var_data)) + var_data


def read_auto_str(data, offset):
    if offset >= len(data):
        return "", offset
    flag = data[offset]
    offset += 1
    if flag == 0:
        return "", offset
    if flag == 0xFF:
        if offset + 4 > len(data):
            return "", offset
        strlen = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
    else:
        strlen = flag
    if offset + strlen > len(data):
        return "", offset

    str_data = data[offset:offset+strlen]
    offset += strlen

    decoded = ""
    i = 0
    while i < len(str_data):
        byte = str_data[i]
        if byte < 0x80:
            decoded += chr(byte)
            i += 1
        else:
            count = byte - 0x80
            if i + 1 + count * 2 > len(str_data):
                break
            for j in range(count):
                try:
                    code = struct.unpack('<H', str_data[i+1+j*2:i+3+j*2])[0]
                    if not (0xD800 <= code <= 0xDFFF):
                        decoded += chr(code)
                except Exception:
                    pass
            i += 1 + count * 2
    return decoded, offset


def read_auto_var(data, offset):
    if offset + 4 > len(data):
        return b'', offset
    varlen = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    if varlen == 0 or offset + varlen > len(data):
        return b'', offset
    return data[offset:offset+varlen], offset + varlen


def find_marker(data, marker):
    return data.find(struct.pack('<I', marker))


# ── Image to PNG bytes ──

def _image_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# ── Binary parsing (2dani → JSON) ──

def _parse_track(kind_data, offset):
    if offset + 4 > len(kind_data):
        return None
    if struct.unpack('<I', kind_data[offset:offset+4])[0] != STR_2danitrack:
        return None
    offset += 4

    if offset + 1 > len(kind_data):
        return None
    track_version = kind_data[offset]
    offset += 1

    track_name, offset = read_auto_str(kind_data, offset)

    if offset + 4 > len(kind_data):
        return None
    img_index = struct.unpack('<I', kind_data[offset:offset+4])[0]
    offset += 4

    if offset + 8 > len(kind_data):
        return None
    end_time = struct.unpack('<f', kind_data[offset:offset+4])[0]
    loop_time = struct.unpack('<f', kind_data[offset+4:offset+8])[0]
    offset += 8

    if offset + 2 > len(kind_data):
        return None
    interpolation_kind = kind_data[offset]
    loop_mode = kind_data[offset+1]
    offset += 2

    blend_mode = 1
    if track_version >= 2:
        if offset + 1 > len(kind_data):
            return None
        blend_mode = kind_data[offset]
        offset += 1

    if offset + 6 > len(kind_data):
        return None
    key_frame_count = struct.unpack('<H', kind_data[offset:offset+2])[0]
    vertex_count = struct.unpack('<H', kind_data[offset+2:offset+4])[0]
    grid_w = kind_data[offset+4]
    grid_h = kind_data[offset+5]
    offset += 6

    if offset + 1 > len(kind_data):
        return None
    key_size = kind_data[offset]
    offset += 1

    key_frames = []
    for _ in range(key_frame_count):
        if offset + key_size > len(kind_data):
            return None
        t = struct.unpack('<f', kind_data[offset:offset+4])[0]
        flag = struct.unpack('<I', kind_data[offset+4:offset+8])[0]
        offset += key_size
        key_frames.append({"time": t, "flag": flag, "vertices": []})

    if offset + 1 > len(kind_data):
        return None
    key_pt_size = kind_data[offset]
    offset += 1

    for kf in key_frames:
        for _ in range(vertex_count):
            if offset + key_pt_size > len(kind_data):
                return None
            pos = list(struct.unpack('<fff', kind_data[offset:offset+12]))
            uv = list(struct.unpack('<ff', kind_data[offset+12:offset+20]))
            color = struct.unpack('<I', kind_data[offset+20:offset+24])[0]
            offset += key_pt_size
            kf["vertices"].append({"position": pos, "uv": uv, "color": color})

    if offset + 1 > len(kind_data):
        return None
    offset += 1  # end flag

    return {
        "name": track_name, "img_index": img_index,
        "end_time": end_time, "loop_time": loop_time,
        "interpolation_kind": interpolation_kind, "loop_mode": loop_mode,
        "blend_mode": blend_mode, "key_frames": key_frames,
        "next_offset": offset,
    }


def _parse_kind(kind_data):
    offset = 0
    if len(kind_data) < 4:
        return None
    if struct.unpack('<I', kind_data[offset:offset+4])[0] != STR_2danikind:
        return None
    offset += 4

    if offset + 1 > len(kind_data):
        return None
    offset += 1  # version

    kind_name, offset = read_auto_str(kind_data, offset)

    if offset + 1 > len(kind_data):
        return None
    loop = kind_data[offset] != 0
    offset += 1

    if offset + 4 > len(kind_data):
        return None
    max_frame_time = struct.unpack('<f', kind_data[offset:offset+4])[0]
    offset += 4

    # Display rect (4 floats = 16 bytes)
    if offset + 16 > len(kind_data):
        return None
    offset += 16

    # Point rect flag
    if offset + 1 > len(kind_data):
        return None
    point_flag = kind_data[offset]
    offset += 1
    if point_flag != 0:
        if offset + 16 + 128 > len(kind_data):
            return None
        offset += 16 + 128

    if offset + 2 > len(kind_data):
        return None
    track_count = struct.unpack('<H', kind_data[offset:offset+2])[0]
    offset += 2

    if track_count > 1000:
        # Recovery: try nearby offsets
        offset -= 2
        for i in range(-5, 6):
            test = offset + i
            if 0 <= test + 2 <= len(kind_data):
                tc = struct.unpack('<H', kind_data[test:test+2])[0]
                if tc <= 1000:
                    track_count = tc
                    offset = test + 2
                    break

    tracks = []
    for _ in range(track_count):
        track = _parse_track(kind_data, offset)
        if track:
            tracks.append(track)
            offset = track['next_offset']
        else:
            break

    return {"name": kind_name, "loop": loop, "max_frame_time": max_frame_time, "tracks": tracks}


def _process_binary_data(bin_data, link_images, extracted_images, base_name):
    """Try to extract image from binary data."""
    try:
        fmt = detect_image_format(bin_data)
        if fmt:
            img = parse_image_data(bin_data)
            name = f"{base_name}_{len(link_images)+1}.png" if base_name else f"image_{len(link_images)+1}.png"
            link_images.append(name)
            extracted_images.append((name, _image_to_png_bytes(img)))
            return
    except Exception:
        pass

    # Fallback: search for image path strings
    for encoding in ('utf-8', 'utf-16le', 'gbk'):
        try:
            decoded = bin_data.decode(encoding, errors='ignore')
            matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', decoded)
            for m in matches:
                m = m.strip()
                if m:
                    link_images.append(m)
        except Exception:
            pass


def _parse_var_link_images(var_data, base_name=None):
    """Parse GVar link images data."""
    link_images = []
    extracted_images = []

    if not var_data:
        return link_images, extracted_images

    var_offset = 0
    if len(var_data) >= 1 and var_data[0] == 0x8F:
        var_offset = 1
    elif len(var_data) >= 4 and struct.unpack('<I', var_data[0:4])[0] == 0x20000000:
        var_offset = 4

    if var_offset < len(var_data):
        flag = var_data[var_offset]
        if (flag & 0xC0) == 0xC0:
            count = flag & 0x3F
            var_offset += 1
            for _ in range(count):
                if var_offset >= len(var_data):
                    break
                item_flag = var_data[var_offset]
                var_offset += 1

                if item_flag == 0xAD:  # EXTSAVE_BIN_DWORD
                    if var_offset + 4 <= len(var_data):
                        bin_len = struct.unpack('<I', var_data[var_offset:var_offset+4])[0]
                        var_offset += 4
                        if var_offset + bin_len <= len(var_data):
                            _process_binary_data(
                                var_data[var_offset:var_offset+bin_len],
                                link_images, extracted_images, base_name)
                            var_offset += bin_len
                elif item_flag == 0xAC:  # EXTSAVE_BIN_WORD
                    if var_offset + 2 <= len(var_data):
                        bin_len = struct.unpack('<H', var_data[var_offset:var_offset+2])[0]
                        var_offset += 2
                        if var_offset + bin_len <= len(var_data):
                            _process_binary_data(
                                var_data[var_offset:var_offset+bin_len],
                                link_images, extracted_images, base_name)
                            var_offset += bin_len

    # Fallback: search raw data for paths
    if not link_images:
        for encoding in ('utf-8', 'utf-16le', 'gbk'):
            try:
                decoded = var_data.decode(encoding, errors='ignore')
                matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', decoded)
                link_images.extend(m.strip() for m in matches if m.strip())
            except Exception:
                pass
        link_images = list(set(link_images))

    return link_images, extracted_images


def _try_extract_image(data, link_images, extracted_images, base_name):
    """Try to extract image from data using format detection."""
    try:
        fmt = detect_image_format(data)
        if fmt:
            img = parse_image_data(data)
            name = f"{base_name}_{len(link_images)+1}.png" if base_name else f"image_{len(link_images)+1}.png"
            link_images.append(name)
            extracted_images.append((name, _image_to_png_bytes(img)))
    except Exception:
        pass


def _parse_common(ani_data, base_name=None):
    """Parse common header. Returns (name, var_data, offset, anim_data, link_images, extracted_images)."""
    # Find ANIFILE_FLAG from end
    flag_pos = -1
    for i in range(len(ani_data) - 4, 0, -1):
        if struct.unpack('<I', ani_data[i:i+4])[0] == ANIFILE_FLAG:
            flag_pos = i
            break
    if flag_pos == -1:
        return None, None, None, None, [], []

    dataoffset = struct.unpack('<I', ani_data[flag_pos+8:flag_pos+12])[0]
    if dataoffset >= len(ani_data):
        return None, None, None, None, [], []

    anim_data = ani_data[dataoffset:]
    data_start = find_marker(anim_data, STR_2danidata)
    if data_start == -1:
        return None, None, None, None, [], []

    offset = data_start + 4
    animation_name, offset = read_auto_str(anim_data, offset)
    var_data, offset = read_auto_var(anim_data, offset)

    link_images = []
    extracted_images = []

    # Always parse var_data first — it contains the actual track images
    if var_data:
        link_images, extracted_images = _parse_var_link_images(var_data, base_name)

    # If var_data had no images, try extracting from full file / anim_data
    if not link_images:
        _try_extract_image(ani_data, link_images, extracted_images, base_name)
    if not link_images:
        _try_extract_image(anim_data, link_images, extracted_images, base_name)

    # Fallback: string search
    if not link_images:
        for encoding in ('utf-8', 'utf-16le', 'gbk'):
            try:
                decoded = ani_data.decode(encoding, errors='ignore')
                matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', decoded)
                link_images.extend(m.strip() for m in matches if m.strip())
            except Exception:
                pass
        link_images = list(set(link_images))

    # If link_images found but no extracted data, try extract from ani_data
    if link_images and not extracted_images:
        _try_extract_image(ani_data, [], extracted_images, base_name or "image")

    return animation_name, var_data, offset, anim_data, link_images, extracted_images


def _parse_kinds(anim_data, offset):
    kinds = []
    while offset + 8 <= len(anim_data):
        flag = struct.unpack('<I', anim_data[offset:offset+4])[0]
        datasize = struct.unpack('<I', anim_data[offset+4:offset+8])[0]
        offset += 8
        if flag == STR_2danikind:
            if offset + datasize > len(anim_data):
                break
            kind = _parse_kind(anim_data[offset:offset+datasize])
            if kind:
                kinds.append(kind)
            offset += datasize
        elif flag == ANIFILE_FLAG:
            break
    return kinds


def parse_2dani_to_json(ani_data, output_dir=None, base_name=None):
    """Parse 2dani binary to JSON dict. If output_dir given, extract images to files."""
    result = {"animation": {"name": "", "link_images": [], "kinds": []}}

    name, var_data, offset, anim_data, link_images, extracted_images = _parse_common(ani_data, base_name)
    if name is None:
        return result

    result["animation"]["name"] = name
    result["animation"]["link_images"] = link_images

    if output_dir and extracted_images:
        os.makedirs(output_dir, exist_ok=True)
        for img_name, img_data in extracted_images:
            with open(os.path.join(output_dir, img_name), 'wb') as f:
                f.write(img_data)

    result["animation"]["kinds"] = _parse_kinds(anim_data, offset)
    return result


def parse_2dani_to_json_with_embedded_images(ani_data, base_name=None):
    """Parse 2dani binary to JSON dict with base64-embedded images."""
    import base64
    result = {"animation": {"name": "", "link_images": [], "images": [], "kinds": []}}

    name, var_data, offset, anim_data, link_images, extracted_images = _parse_common(ani_data, base_name)
    if name is None:
        return result

    result["animation"]["name"] = name

    for img_name, img_data in extracted_images:
        b64 = base64.b64encode(img_data).decode('utf-8')
        result["animation"]["images"].append({
            "name": img_name,
            "data": f"data:image/png;base64,{b64}"
        })

    if not extracted_images:
        _try_extract_image(ani_data, [], extracted_images, base_name or "image")
        for img_name, img_data in extracted_images:
            b64 = base64.b64encode(img_data).decode('utf-8')
            result["animation"]["images"].append({
                "name": img_name,
                "data": f"data:image/png;base64,{b64}"
            })

    result["animation"]["kinds"] = _parse_kinds(anim_data, offset)
    return result


# ── Binary serialization (JSON → 2dani) ──

def create_2dani_from_json(json_data, preview_image_path="", embed_binary=False):
    """Serialize JSON animation data to 2dani binary format."""
    animation = json_data['animation']

    # Preview image
    if preview_image_path and os.path.exists(preview_image_path):
        img = Image.open(preview_image_path)
        width, height = img.size
        preview_data = _image_to_png_bytes(img)
    else:
        img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
        width, height = 1, 1
        preview_data = _image_to_png_bytes(img)

    preview_size = len(preview_data)
    buf = bytearray()

    # Header marker
    buf.extend(struct.pack('<I', STR_2danidata))
    buf.extend(write_auto_str(animation.get('name', '')))

    # Link images as GVar array
    link_images = animation.get('link_images', [])
    var_buf = bytearray()
    var_buf.append(0xC0 | len(link_images))

    for img_path in link_images:
        if embed_binary:
            img_data = b''
            try:
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                else:
                    base = os.path.basename(img_path)
                    if os.path.exists(base):
                        with open(base, 'rb') as f:
                            img_data = f.read()
            except Exception:
                pass

            if img_data:
                var_buf.append(0xAD)  # EXTSAVE_BIN_DWORD
                var_buf.extend(struct.pack('<I', len(img_data)))
                var_buf.extend(img_data)
            else:
                var_buf.append(0xB2)  # EXTSAVE_STR_WORD
                gbox = write_gbox_unicode(img_path)
                var_buf.extend(struct.pack('<H', len(gbox)))
                var_buf.extend(gbox)
        else:
            var_buf.append(0xB2)
            gbox = write_gbox_unicode(img_path)
            var_buf.extend(struct.pack('<H', len(gbox)))
            var_buf.extend(gbox)

    buf.extend(write_auto_var(var_buf))

    # Kinds
    for kind in animation.get('kinds', []):
        kind_buf = bytearray()
        kind_buf.extend(struct.pack('<I', STR_2danikind))
        kind_buf.append(1)  # version
        kind_buf.extend(write_auto_str(kind.get('name', 'Idle')))
        kind_buf.append(1 if kind.get('loop', True) else 0)
        kind_buf.extend(struct.pack('<f', kind.get('max_frame_time', 0.1)))
        kind_buf.extend(struct.pack('<ffff', -100, -100, 100, 100))  # display rect
        kind_buf.append(0)  # no point rect

        tracks = kind.get('tracks', [])
        kind_buf.extend(struct.pack('<H', len(tracks)))

        for track in tracks:
            tb = bytearray()
            tb.extend(struct.pack('<I', STR_2danitrack))
            tb.append(2)  # version
            tb.extend(write_auto_str(track.get('name', 'Main')))
            tb.extend(struct.pack('<I', track.get('img_index', 0)))
            tb.extend(struct.pack('<f', track.get('end_time', 0.1)))
            tb.extend(struct.pack('<f', track.get('loop_time', 0.1)))
            tb.append(track.get('interpolation_kind', 1))
            tb.append(track.get('loop_mode', 0))
            tb.append(track.get('blend_mode', 1))

            kfs = track.get('key_frames', [])
            vertex_count = track.get('vertex_count', 4)
            tb.extend(struct.pack('<H', len(kfs)))
            tb.extend(struct.pack('<H', vertex_count))
            tb.append(track.get('grid_w', 1))
            tb.append(track.get('grid_h', 1))

            tb.append(8)  # key_size
            for kf in kfs:
                tb.extend(struct.pack('<f', kf.get('time', 0.0)))
                tb.extend(struct.pack('<I', kf.get('flag', 0)))

            tb.append(24)  # key_pt_size
            for kf in kfs:
                for v in kf.get('vertices', []):
                    pos = v.get('position', [0, 0, 0])
                    tb.extend(struct.pack('<fff', *pos))
                    uv = v.get('uv', [0, 0])
                    tb.extend(struct.pack('<ff', *uv))
                    tb.extend(struct.pack('<I', v.get('color', W_COLOR)))

            tb.append(0)  # end flag
            kind_buf.extend(tb)

        kind_buf.append(0)  # kind end flag

        buf.extend(struct.pack('<I', STR_2danikind))
        buf.extend(struct.pack('<I', len(kind_buf)))
        buf.extend(kind_buf)

    # File footer
    buf.extend(struct.pack('<I', ANIFILE_FLAG))
    buf.extend(struct.pack('<I', ANIFILE_VER))
    buf.extend(struct.pack('<I', preview_size))
    buf.extend(struct.pack('<I', 0))

    return preview_data + buf


def create_2dani_from_image(image_path, width, height, center_x=None, center_y=None, embed_binary=False):
    """Create single-frame 2dani from an image file."""
    if center_x is None:
        center_x = width / 2
    if center_y is None:
        center_y = height / 2

    img_name = os.path.basename(image_path)
    img_name = ''.join(c for c in img_name if c.isalnum() or c in '_.-')
    link_imgs = [image_path] if embed_binary else [img_name]

    json_data = {
        "animation": {
            "name": "animation",
            "link_images": link_imgs,
            "kinds": [{
                "name": "std",
                "loop": True,
                "max_frame_time": 0.0,
                "tracks": [{
                    "name": "",
                    "img_index": 0,
                    "end_time": 0.0,
                    "loop_time": 0.0,
                    "interpolation_kind": 1,
                    "loop_mode": 1,
                    "blend_mode": 1,
                    "key_frames": [{
                        "time": 0.0,
                        "flag": 0x00020000,
                        "vertices": [
                            {"position": [-center_x, -center_y, 0], "uv": [0, 0], "color": W_COLOR},
                            {"position": [-center_x + width, -center_y, 0], "uv": [1, 0], "color": W_COLOR},
                            {"position": [-center_x, -center_y + height, 0], "uv": [0, 1], "color": W_COLOR},
                            {"position": [-center_x + width, -center_y + height, 0], "uv": [1, 1], "color": W_COLOR},
                        ]
                    }]
                }]
            }]
        }
    }
    return create_2dani_from_json(json_data, image_path, embed_binary=embed_binary)
