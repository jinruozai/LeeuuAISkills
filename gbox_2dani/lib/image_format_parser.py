"""GBox image format parser - supports PNG, JPEG, GIF, JGEIMGFLAG, IMG1, ALE formats."""

import struct
import io
from PIL import Image

JGEIMGFLAG = 0xF6BDCA96


def detect_image_format(data):
    """Detect image format from binary data header."""
    if not data:
        return None

    # Check file header first
    if data.startswith(b'\x89PNG'):
        return 'png'
    if data.startswith(b'\xff\xd8'):
        return 'jpeg'
    if data.startswith(b'GIF89a') or data.startswith(b'GIF87a'):
        return 'gif'

    # Check ALE format
    for marker in (b'ALE', b'AEX'):
        if data.find(marker) != -1:
            return 'ale'

    # Check JGEIMGFLAG format
    for i in range(len(data) - 4):
        flag = struct.unpack('<I', data[i:i+4])[0]
        if flag == JGEIMGFLAG and i + 32 <= len(data):
            try:
                ver = struct.unpack('<I', data[i+4:i+8])[0]
                width = struct.unpack('<I', data[i+8:i+12])[0]
                height = struct.unpack('<I', data[i+12:i+16])[0]
                jpgoffset = struct.unpack('<I', data[i+16:i+20])[0]
                jpglen = struct.unpack('<I', data[i+20:i+24])[0]
                gifoffset = struct.unpack('<I', data[i+24:i+28])[0]
                giflen = struct.unpack('<I', data[i+28:i+32])[0]
                if (ver == 1 and 0 < width <= 2048 and 0 < height <= 2048
                        and jpgoffset + jpglen <= len(data) - i
                        and gifoffset + giflen <= len(data) - i
                        and jpglen > 0 and giflen > 0):
                    return 'jgeimg'
            except Exception:
                pass

    # Search for embedded standard formats
    if data.find(b'\xff\xd8') != -1:
        return 'jpeg'
    if data.find(b'\x89PNG') != -1:
        return 'png'

    for marker in (b'GIF89a', b'GIF87a'):
        pos = data.find(marker)
        if pos != -1 and pos + 10 <= len(data):
            w = struct.unpack('<H', data[pos+6:pos+8])[0]
            h = struct.unpack('<H', data[pos+8:pos+10])[0]
            if w > 2 and h > 2:
                return 'gif'

    # Check IMG1 format
    flag_img1 = 0x494D4731
    for i in range(len(data) - 4):
        if struct.unpack('I', data[i:i+4])[0] == flag_img1:
            return 'img1'

    return None


def find_image_data(data):
    """Find image data start position. Returns (format, offset) or (None, None)."""
    if not data:
        return None, None

    if data.startswith(b'\x89PNG'):
        return 'png', 0
    if data.startswith(b'\xff\xd8'):
        return 'jpeg', 0
    if data.startswith(b'GIF89a') or data.startswith(b'GIF87a'):
        return 'gif', 0

    for marker in (b'ALE', b'AEX'):
        pos = data.find(marker)
        if pos != -1:
            return 'ale', pos

    # JGEIMGFLAG
    for i in range(len(data) - 4):
        flag = struct.unpack('<I', data[i:i+4])[0]
        if flag == JGEIMGFLAG and i + 32 <= len(data):
            try:
                ver = struct.unpack('<I', data[i+4:i+8])[0]
                width = struct.unpack('<I', data[i+8:i+12])[0]
                height = struct.unpack('<I', data[i+12:i+16])[0]
                jpgoffset = struct.unpack('<I', data[i+16:i+20])[0]
                jpglen = struct.unpack('<I', data[i+20:i+24])[0]
                gifoffset = struct.unpack('<I', data[i+24:i+28])[0]
                giflen = struct.unpack('<I', data[i+28:i+32])[0]
                if (ver == 1 and 0 < width <= 2048 and 0 < height <= 2048
                        and jpgoffset + jpglen <= len(data) - i
                        and gifoffset + giflen <= len(data) - i
                        and jpglen > 0 and giflen > 0):
                    return 'jgeimg', i
            except Exception:
                pass

    jpeg_pos = data.find(b'\xff\xd8')
    if jpeg_pos != -1:
        return 'jpeg', jpeg_pos

    png_pos = data.find(b'\x89PNG')
    if png_pos != -1:
        return 'png', png_pos

    for marker in (b'GIF89a', b'GIF87a'):
        pos = data.find(marker)
        if pos != -1 and pos + 10 <= len(data):
            w = struct.unpack('<H', data[pos+6:pos+8])[0]
            h = struct.unpack('<H', data[pos+8:pos+10])[0]
            if w > 2 and h > 2:
                return 'gif', pos

    flag_img1 = 0x494D4731
    for i in range(len(data) - 4):
        if struct.unpack('I', data[i:i+4])[0] == flag_img1:
            return 'img1', i

    return None, None


def parse_image_data(data):
    """Parse image data and return PIL Image."""
    fmt, pos = find_image_data(data)
    if fmt is None:
        raise ValueError("No image data found")

    image_data = data[pos:]
    parsers = {
        'png': _parse_standard,
        'jpeg': _parse_standard,
        'gif': _parse_standard,
        'ale': _parse_ale,
        'img1': _parse_img1,
        'jgeimg': _parse_jgeimg,
    }
    parser = parsers.get(fmt)
    if not parser:
        raise ValueError(f"Unknown image format: {fmt}")
    return parser(image_data)


def _parse_standard(data):
    return Image.open(io.BytesIO(data))


def _parse_ale(data):
    try:
        from ale_parser import ALEParser
        return ALEParser(data).to_pil_image()
    except Exception as e:
        raise ValueError(f"Failed to parse ALE: {e}")


def _parse_img1(data):
    offset = 4  # FLAG_IMG1
    total_size = struct.unpack('I', data[offset:offset+4])[0]
    offset += 4
    kind = struct.unpack('I', data[offset:offset+4])[0]
    offset += 4
    width = struct.unpack('I', data[offset:offset+4])[0]
    offset += 4
    height = struct.unpack('I', data[offset:offset+4])[0]
    offset += 4

    kind_map = {
        0x0040: (4, 'RGBA'),
        0x0030: (3, 'RGB'),
        0x0011: (1, 'L'),
        0x0021: (2, 'RGB'),  # RGB565
    }
    if kind not in kind_map:
        raise ValueError(f"Unsupported IMG1 kind: {kind}")

    bpp, mode = kind_map[kind]
    byte_per_line = ((width * bpp) + 3) & ~3
    pixel_data = data[offset:offset + byte_per_line * height]

    if kind == 0x0021:
        rgb_data = b''
        for i in range(0, len(pixel_data), 2):
            if i + 1 < len(pixel_data):
                val = struct.unpack('H', pixel_data[i:i+2])[0]
                r = ((val >> 11) & 0x1F) << 3
                g = ((val >> 5) & 0x3F) << 2
                b = (val & 0x1F) << 3
                rgb_data += struct.pack('BBB', r, g, b)
        return Image.frombytes('RGB', (width, height), rgb_data)

    return Image.frombytes(mode, (width, height), pixel_data, 'raw', mode, 0, 1)


def _parse_jgeimg(data):
    """Parse JGEIMGFLAG: JPEG content + GIF alpha mask → RGBA."""
    ver = struct.unpack('<I', data[4:8])[0]
    width = struct.unpack('<I', data[8:12])[0]
    height = struct.unpack('<I', data[12:16])[0]
    jpgoffset = struct.unpack('<I', data[16:20])[0]
    jpglen = struct.unpack('<I', data[20:24])[0]
    gifoffset = struct.unpack('<I', data[24:28])[0]
    giflen = struct.unpack('<I', data[28:32])[0]

    if ver != 1:
        raise ValueError("Invalid JGEIMGFLAG version")

    jpeg_img = Image.open(io.BytesIO(data[jpgoffset:jpgoffset + jpglen]))
    mask_img = Image.open(io.BytesIO(data[gifoffset:gifoffset + giflen]))

    if mask_img.size != jpeg_img.size:
        mask_img = mask_img.resize(jpeg_img.size, Image.LANCZOS)

    if jpeg_img.mode != 'RGB':
        jpeg_img = jpeg_img.convert('RGB')
    if mask_img.mode != 'L':
        mask_img = mask_img.convert('L')

    # Black = transparent, others = opaque
    alpha = Image.new('L', mask_img.size, 0)
    mask_px = mask_img.load()
    alpha_px = alpha.load()
    for y in range(mask_img.height):
        for x in range(mask_img.width):
            alpha_px[x, y] = 0 if mask_px[x, y] == 0 else 255

    result = jpeg_img.copy()
    result.putalpha(alpha)
    return result
