import os
import struct
import json
from image_format_parser import detect_image_format, parse_image_data, save_image

# 常量定义
ANIFILE_FLAG = 0xB65EB0B0
ANIFILE_VER = 2
STR_2danidata = 0x519C4E66
STR_2danikind = 0x5E74D596
STR_2danitrack = 0xF53FF3EB
W_COLOR = 0xFFFFFFFF

def write_gbox_unicode(s):
    """
    写入GBox引擎的Unicode编码格式
    对于ASCII字符（< 0x80），使用单字节编码
    对于非ASCII字符，使用多字节编码（0x80 + 字符数 + UTF-16 little-endian）
    """
    encoded = bytearray()
    i = 0
    while i < len(s):
        char = s[i]
        code_point = ord(char)
        if code_point < 0x80:
            # ASCII字符，单字节编码
            encoded.append(code_point)
            i += 1
        else:
            # 非ASCII字符，多字节编码
            # 计算连续的非ASCII字符数
            count = 0
            j = i
            while j < len(s) and ord(s[j]) >= 0x80:
                count += 1
                j += 1
            # 写入标志字节（0x80 + 字符数）
            encoded.append(0x80 + count)
            # 写入UTF-16 little-endian编码
            for k in range(i, j):
                encoded.extend(struct.pack('<H', ord(s[k])))
            i = j
    # 确保字符串以null结尾
    encoded.append(0)
    return encoded

def write_auto_str(s):
    """
    写入自动字符串格式
    """
    if not s:
        return b'\x00'
    
    # 使用GBox的Unicode编码格式
    encoded = write_gbox_unicode(s)
    encoded_len = len(encoded)
    
    if encoded_len < 0xFF:
        return struct.pack('<B', encoded_len) + encoded
    else:
        return b'\xFF' + struct.pack('<I', encoded_len) + encoded

def write_auto_var(var_data):
    """
    写入自动变量格式
    """
    if not var_data:
        return struct.pack('<I', 0)
    
    # 直接写入数据，不需要手动添加SAVEVARFLAG_NORMAL头
    # 因为EXTSAVE格式已经包含了必要的头信息
    length = len(var_data)
    return struct.pack('<I', length) + var_data

def find_marker(data, marker):
    """
    在数据中查找标记
    """
    marker_bytes = struct.pack('<I', marker)
    return data.find(marker_bytes)

def read_auto_str(data, offset):
    """
    读取自动字符串格式
    """
    if offset >= len(data):
        return "", offset
    
    flag = data[offset]
    offset += 1
    
    if flag == 0:
        return "", offset
    
    if flag == 0xFF:
        # 长字符串
        if offset + 4 > len(data):
            return "", offset
        strlen = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
    else:
        # 短字符串
        strlen = flag
    
    if offset + strlen > len(data):
        return "", offset
    
    # 读取字符串数据
    str_data = data[offset:offset+strlen]
    offset += strlen
    
    # 尝试解析GBox Unicode编码
    decoded = ""
    i = 0
    while i < len(str_data):
        byte = str_data[i]
        if byte < 0x80:
            # ASCII字符
            decoded += chr(byte)
            i += 1
        else:
            # 非ASCII字符
            count = byte - 0x80
            if i + 1 + count * 2 > len(str_data):
                break
            for j in range(count):
                try:
                    code = struct.unpack('<H', str_data[i+1+j*2:i+3+j*2])[0]
                    # 过滤掉无效的Unicode字符
                    if 0xD800 <= code <= 0xDFFF:
                        # 代理对字符，跳过
                        continue
                    decoded += chr(code)
                except:
                    # 遇到错误，跳过此字符
                    pass
            i += 1 + count * 2
    
    return decoded, offset

def read_auto_var(data, offset):
    """
    读取自动变量格式
    """
    if offset + 4 > len(data):
        return b'', offset
    
    varlen = struct.unpack('<I', data[offset:offset+4])[0]
    offset += 4
    
    if varlen == 0:
        return b'', offset
    
    if offset + varlen > len(data):
        return b'', offset
    
    var_data = data[offset:offset+varlen]
    offset += varlen
    
    return var_data, offset

def process_binary_data(bin_data, link_images, extracted_images, base_name):
    """
    处理二进制数据，尝试提取图片
    """
    # 尝试从二进制数据中提取完整的图片文件
    try:
        # 检测图像格式
        img_format = detect_image_format(bin_data)
        if img_format:
            # 解析图像数据
            img = parse_image_data(bin_data)
            
            # 生成图片文件名
            if base_name:
                img_name = f"{base_name}_{len(link_images) + 1}.png"
            else:
                img_name = f"image_{len(link_images) + 1}.png"
            
            # 保存为PNG格式
            import io
            png_buffer = io.BytesIO()
            img.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            link_images.append(img_name)
            extracted_images.append((img_name, png_data))
    except Exception as e:
        pass
    
    # 尝试直接从二进制数据中提取所有可能的字符串
    encodings = ['utf-8', 'utf-16le', 'gbk']
    for encoding in encodings:
        try:
            decoded = bin_data.decode(encoding, errors='ignore')
            # 清理字符串，只保留可打印字符
            cleaned = ''.join(c for c in decoded if c.isprintable() or c in '\t\n\r')
            # 查找包含图片扩展名的字符串
            import re
            # 匹配可能的图片路径
            matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', cleaned)
            for match in matches:
                if match and not match.isspace():
                    # 清理路径
                    match = match.strip()
                    if match:
                        link_images.append(match)
        except:
            pass

def parse_var_link_images(var_data, output_dir=None, base_name=None):
    """
    使用GVar解析规则解析关联图片数据
    """
    link_images = []
    extracted_images = []  # 存储提取的图片数据 (文件名, 数据)
    
    # 检查数据是否为空
    if not var_data:
        return link_images, extracted_images
    
    # 跳过SAVEVARFLAG_NORMAL头（如果存在）
    var_offset = 0
    if len(var_data) >= 1 and var_data[0] == 0x8F:
        var_offset = 1
    elif len(var_data) >= 4 and struct.unpack('<I', var_data[0:4])[0] == 0x20000000:
        var_offset = 4
    
    # 分析数据结构
    if var_offset < len(var_data):
        flag = var_data[var_offset]
        
        # 处理数组类型
        if (flag & 0xC0) == 0xC0:  # EXTSAVE_SZ_MASK64
            count = flag & 0x3F
            var_offset += 1
            
            for i in range(count):
                if var_offset < len(var_data):
                    item_flag = var_data[var_offset]
                    var_offset += 1
                    
                    # 处理二进制数据类型
                    if item_flag == 0xAD:  # EXTSAVE_BIN_DWORD
                        if var_offset + 4 <= len(var_data):
                            bin_len = struct.unpack('<I', var_data[var_offset:var_offset+4])[0]
                            var_offset += 4
                            
                            if var_offset + bin_len <= len(var_data):
                                bin_data = var_data[var_offset:var_offset+bin_len]
                                var_offset += bin_len
                                
                                # 处理二进制数据
                                process_binary_data(bin_data, link_images, extracted_images, base_name)
                            else:
                                print(f"Warning: Binary data length mismatch. Expected {bin_len}, available {len(var_data) - var_offset}")
                        else:
                            print("Warning: Incomplete binary length data")
                    elif item_flag == 0xAC:  # EXTSAVE_BIN_WORD
                        if var_offset + 2 <= len(var_data):
                            bin_len = struct.unpack('<H', var_data[var_offset:var_offset+2])[0]
                            var_offset += 2
                            
                            if var_offset + bin_len <= len(var_data):
                                bin_data = var_data[var_offset:var_offset+bin_len]
                                var_offset += bin_len
                                
                                # 处理二进制数据
                                process_binary_data(bin_data, link_images, extracted_images, base_name)
    
    # 如果没有找到，尝试直接从整个数据中提取
    if not link_images:
        # 尝试不同的编码
        encodings = ['utf-8', 'utf-16le', 'gbk']
        for encoding in encodings:
            try:
                decoded = var_data[var_offset:].decode(encoding, errors='ignore')
                # 查找包含图片扩展名的字符串
                import re
                # 匹配可能的图片路径
                matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', decoded)
                for match in matches:
                    if match and not match.isspace():
                        link_images.append(match)
            except:
                pass
    
    # 去重
    link_images = list(set(link_images))
    return link_images, extracted_images

def parse_track_data(kind_data, offset):
    """
    解析轨道数据
    """
    # 读取轨道标志
    if offset + 4 > len(kind_data):
        return None
    track_flag = struct.unpack('<I', kind_data[offset:offset+4])[0]
    if track_flag != STR_2danitrack:
        return None
    offset += 4
    
    # 读取轨道版本
    if offset + 1 > len(kind_data):
        return None
    track_version = kind_data[offset]
    offset += 1
    
    # 读取轨道名称
    track_name, offset = read_auto_str(kind_data, offset)
    
    # 读取图片索引
    if offset + 4 > len(kind_data):
        return None
    img_index = struct.unpack('<I', kind_data[offset:offset+4])[0]
    offset += 4
    
    # 读取结束时间和循环时间
    if offset + 8 > len(kind_data):
        return None
    end_time = struct.unpack('<f', kind_data[offset:offset+4])[0]
    loop_time = struct.unpack('<f', kind_data[offset+4:offset+8])[0]
    offset += 8
    
    # 读取插值方式、循环模式
    if offset + 2 > len(kind_data):
        return None
    interpolation_kind = kind_data[offset]
    loop_mode = kind_data[offset+1]
    offset += 2
    
    # 读取混合模式（如果版本 >= 2）
    blend_mode = 1  # 默认混合模式
    if track_version >= 2:
        if offset + 1 > len(kind_data):
            return None
        blend_mode = kind_data[offset]
        offset += 1
    
    # 读取关键帧数量、顶点数量、网格大小
    if offset + 6 > len(kind_data):
        return None
    key_frame_count = struct.unpack('<H', kind_data[offset:offset+2])[0]
    vertex_count = struct.unpack('<H', kind_data[offset+2:offset+4])[0]
    grid_w = kind_data[offset+4]
    grid_h = kind_data[offset+5]
    offset += 6
    
    # 读取关键帧定义大小
    if offset + 1 > len(kind_data):
        return None
    key_size = kind_data[offset]
    offset += 1
    
    # 读取关键帧定义
    key_frames = []
    for _ in range(key_frame_count):
        if offset + key_size > len(kind_data):
            return None
        # 读取时间和标志
        time = struct.unpack('<f', kind_data[offset:offset+4])[0]
        flag = struct.unpack('<I', kind_data[offset+4:offset+8])[0]
        offset += key_size
        
        key_frames.append({"time": time, "flag": flag, "vertices": []})
    
    # 读取关键帧数据大小
    if offset + 1 > len(kind_data):
        return None
    key_pt_size = kind_data[offset]
    offset += 1
    
    # 读取关键帧数据
    for i, key_frame in enumerate(key_frames):
        for _ in range(vertex_count):
            if offset + key_pt_size > len(kind_data):
                return None
            # 读取位置
            pos = struct.unpack('<fff', kind_data[offset:offset+12])
            # 读取UV
            uv = struct.unpack('<ff', kind_data[offset+12:offset+20])
            # 读取颜色
            color = struct.unpack('<I', kind_data[offset+20:offset+24])[0]
            offset += key_pt_size
            
            key_frame["vertices"].append({
                "position": list(pos),
                "uv": list(uv),
                "color": color
            })
    
    # 读取结束标志
    if offset + 1 > len(kind_data):
        return None
    end_flag = kind_data[offset]
    offset += 1
    
    return {
        "name": track_name,
        "img_index": img_index,
        "end_time": end_time,
        "loop_time": loop_time,
        "interpolation_kind": interpolation_kind,
        "loop_mode": loop_mode,
        "blend_mode": blend_mode,
        "key_frames": key_frames,
        "next_offset": offset
    }

def parse_kind_data(kind_data):
    """
    解析Kind数据
    """
    kind_offset = 0
    
    # 检查数据长度
    if len(kind_data) < 4:
        return None
    
    # 跳过STR_2danikind标记
    if struct.unpack('<I', kind_data[kind_offset:kind_offset+4])[0] != STR_2danikind:
        return None
    kind_offset += 4
    
    # 读取版本
    if kind_offset + 1 > len(kind_data):
        return None
    version = kind_data[kind_offset]
    kind_offset += 1
    
    # 读取kind名称
    kind_name, kind_offset = read_auto_str(kind_data, kind_offset)
    
    # 读取循环标志
    if kind_offset + 1 > len(kind_data):
        return None
    loop = kind_data[kind_offset] != 0
    kind_offset += 1
    
    # 读取最大帧时间
    if kind_offset + 4 > len(kind_data):
        return None
    max_frame_time = struct.unpack('<f', kind_data[kind_offset:kind_offset+4])[0]
    kind_offset += 4
    
    # 读取显示矩形
    if kind_offset + 16 > len(kind_data):
        return None
    kind_offset += 16
    
    # 读取点矩形标志
    if kind_offset + 1 > len(kind_data):
        return None
    point_flag = kind_data[kind_offset]
    kind_offset += 1
    if point_flag != 0:
        # 读取点矩形数据
        # GRect结构是4个int，共16字节，加上32个DWORD（128字节）
        if kind_offset + 16 + 32 * 4 > len(kind_data):
            return None
        kind_offset += 16 + 32 * 4
    
    # 读取轨道数量
    if kind_offset + 2 > len(kind_data):
        return None
    track_count = struct.unpack('<H', kind_data[kind_offset:kind_offset+2])[0]
    kind_offset += 2
    
    # 检查轨道数量是否合理
    if track_count > 1000:
        # 尝试重新解析，可能是偏移量计算错误
        # 回退到之前的位置，重新计算
        kind_offset -= 2
        
        # 尝试不同的偏移量
        for i in range(-5, 6):
            test_offset = kind_offset + i
            if 0 <= test_offset + 2 <= len(kind_data):
                test_count = struct.unpack('<H', kind_data[test_offset:test_offset+2])[0]
                if test_count <= 1000:
                    track_count = test_count
                    kind_offset = test_offset + 2
                    break
        
        if track_count > 1000:
            # 尝试读取4字节作为轨道数量
            if kind_offset + 4 <= len(kind_data):
                track_count = struct.unpack('<I', kind_data[kind_offset:kind_offset+4])[0]
                kind_offset += 4
    
    tracks = []
    for _ in range(track_count):
        # 解析轨道数据
        track_info = parse_track_data(kind_data, kind_offset)
        if track_info:
            tracks.append(track_info)
            kind_offset = track_info['next_offset']
        else:
            break
    
    return {
        "name": kind_name,
        "loop": loop,
        "max_frame_time": max_frame_time,
        "tracks": tracks
    }

def _parse_2dani_common(ani_data, base_name=None):
    """
    解析2dani.bmp数据的公共部分
    返回：(animation_name, var_data, offset, anim_data, link_images, extracted_images)
    """
    # 查找文件末尾的ANIFILE_FLAG
    # 从文件末尾开始查找
    flag_pos = -1
    for i in range(len(ani_data) - 4, 0, -1):
        if struct.unpack('<I', ani_data[i:i+4])[0] == ANIFILE_FLAG:
            flag_pos = i
            break
    
    if flag_pos == -1:
        return None, None, None, None, [], []
    
    # 读取版本和数据偏移量
    version = struct.unpack('<I', ani_data[flag_pos+4:flag_pos+8])[0]
    dataoffset = struct.unpack('<I', ani_data[flag_pos+8:flag_pos+12])[0]
    
    # 从数据偏移量开始分析
    if dataoffset >= len(ani_data):
        return None, None, None, None, [], []
    
    anim_data = ani_data[dataoffset:]
    
    # 查找STR_2danidata
    data_start = find_marker(anim_data, STR_2danidata)
    if data_start == -1:
        return None, None, None, None, [], []
    
    # 读取动画名称
    offset = data_start + 4
    animation_name, offset = read_auto_str(anim_data, offset)
    
    # 读取关联图片数据 - 使用GVar解析规则
    var_data, offset = read_auto_var(anim_data, offset)
    link_images = []
    extracted_images = []
    
    # 首先尝试在整个ani_data中搜索JGEIMGFLAG格式
    try:
        # 检测图像格式
        img_format = detect_image_format(ani_data)
        if img_format == 'jgeimg':
            # 解析图像数据
            img = parse_image_data(ani_data)
            
            # 生成图片文件名
            if base_name:
                img_name = f"{base_name}_{len(link_images) + 1}.png"
            else:
                img_name = f"image_{len(link_images) + 1}.png"
            
            # 保存为PNG格式
            import io
            png_buffer = io.BytesIO()
            img.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            link_images.append(img_name)
            extracted_images.append((img_name, png_data))
    except Exception as e:
        pass
    
    # 如果没有找到JGEIMGFLAG格式，再尝试解析var_data
    if not link_images and var_data:
        # 直接解析GVar数据，因为link_images是一个字符串数组
        link_images, extracted_images = parse_var_link_images(var_data, None, base_name)
    
    # 如果仍然没有找到图片，尝试在anim_data中搜索JGEIMGFLAG格式
    if not link_images:
        try:
            # 检测图像格式
            img_format = detect_image_format(anim_data)
            if img_format == 'jgeimg':
                # 解析图像数据
                img = parse_image_data(anim_data)
                
                # 生成图片文件名
                if base_name:
                    img_name = f"{base_name}_{len(link_images) + 1}.png"
                else:
                    img_name = f"image_{len(link_images) + 1}.png"
                
                # 保存为PNG格式
                import io
                png_buffer = io.BytesIO()
                img.save(png_buffer, format='PNG')
                png_data = png_buffer.getvalue()
                
                link_images.append(img_name)
                extracted_images.append((img_name, png_data))
        except Exception as e:
            pass
    
    # 如果没有找到link_images，尝试直接从文件中提取
    if not link_images:
        # 尝试不同的编码
        encodings = ['utf-8', 'utf-16le', 'gbk']
        for encoding in encodings:
            try:
                decoded = ani_data.decode(encoding, errors='ignore')
                # 查找包含图片扩展名的字符串
                import re
                # 匹配可能的图片路径
                matches = re.findall(r'[a-zA-Z0-9_./\\-]+\.(?:png|jpg|jpeg|bmp)', decoded)
                for match in matches:
                    if match and not match.isspace():
                        link_images.append(match)
            except:
                pass
        # 去重
        link_images = list(set(link_images))
    
    # 如果link_images中有数据但extracted_images为空，尝试从link_images中提取图片
    if link_images and not extracted_images:
        for img_name in link_images:
            # 尝试从ani_data中提取图片数据
            try:
                # 检测图像格式
                img_format = detect_image_format(ani_data)
                if img_format:
                    # 解析图像数据
                    img = parse_image_data(ani_data)
                    
                    # 保存为PNG格式
                    import io
                    png_buffer = io.BytesIO()
                    img.save(png_buffer, format='PNG')
                    png_data = png_buffer.getvalue()
                    
                    extracted_images.append((img_name, png_data))
                    break
            except Exception as e:
                pass
    
    return animation_name, var_data, offset, anim_data, link_images, extracted_images

def _parse_kinds_data(anim_data, offset):
    """
    解析kinds数据
    """
    kinds = []
    while offset + 8 <= len(anim_data):
        # 读取flag和datasize
        flag = struct.unpack('<I', anim_data[offset:offset+4])[0]
        datasize = struct.unpack('<I', anim_data[offset+4:offset+8])[0]
        offset += 8
        
        if flag == STR_2danikind:
            if offset + datasize > len(anim_data):
                break
            
            kind_data = anim_data[offset:offset+datasize]
            offset += datasize
            
            # 解析kind数据
            kind_info = parse_kind_data(kind_data)
            if kind_info:
                kinds.append(kind_info)
        elif flag == ANIFILE_FLAG:
            # 结束
            break
    return kinds

def parse_2dani_to_json(ani_data, output_dir=None, base_name=None):
    """
    将2dani.bmp数据转换为JSON格式
    """
    result = {"animation": {
        "name": "",
        "link_images": [],
        "kinds": []
    }}
    
    # 解析公共部分
    animation_name, var_data, offset, anim_data, link_images, extracted_images = _parse_2dani_common(ani_data, base_name)
    
    if animation_name is None:
        return result
    
    result["animation"]["name"] = animation_name
    result["animation"]["link_images"] = link_images
    
    # 保存提取的图片到输出目录
    if output_dir and extracted_images:
        for img_name, img_data in extracted_images:
            img_path = os.path.join(output_dir, img_name)
            with open(img_path, 'wb') as f:
                f.write(img_data)
    
    # 解析kinds数据
    kinds = _parse_kinds_data(anim_data, offset)
    result["animation"]["kinds"] = kinds
    
    return result

def parse_2dani_to_json_with_embedded_images(ani_data, base_name=None):
    """
    将2dani.bmp数据转换为包含图片二进制数据的JSON格式
    图片数据以base64编码存储在JSON中
    """
    result = {"animation": {
        "name": "",
        "link_images": [],
        "images": [],  # 存储base64编码的图片数据
        "kinds": []
    }}
    
    # 解析公共部分
    animation_name, var_data, offset, anim_data, link_images, extracted_images = _parse_2dani_common(ani_data, base_name)
    
    if animation_name is None:
        return result
    
    result["animation"]["name"] = animation_name
    result["animation"]["link_images"] = []
    
    # 将提取的图片转换为base64编码
    import base64
    for img_name, img_data in extracted_images:
        base64_data = base64.b64encode(img_data).decode('utf-8')
        result["animation"]["images"].append({
            "name": img_name,
            "data": f"data:image/png;base64,{base64_data}"
        })
    
    # 如果extracted_images为空，尝试从ani_data中提取图片
    if not extracted_images:
        try:
            # 检测图像格式
            img_format = detect_image_format(ani_data)
            if img_format:
                # 解析图像数据
                img = parse_image_data(ani_data)
                
                # 生成图片文件名
                if base_name:
                    img_name = f"{base_name}_1.png"
                else:
                    img_name = "image_1.png"
                
                # 保存为PNG格式
                import io
                png_buffer = io.BytesIO()
                img.save(png_buffer, format='PNG')
                png_data = png_buffer.getvalue()
                
                # 转换为base64编码
                base64_data = base64.b64encode(png_data).decode('utf-8')
                result["animation"]["images"].append({
                    "name": img_name,
                    "data": f"data:image/png;base64,{base64_data}"
                })
        except Exception as e:
            pass
    
    # 解析kinds数据
    kinds = _parse_kinds_data(anim_data, offset)
    result["animation"]["kinds"] = kinds
    
    return result

def write_png(img):
    """
    将PIL Image对象转换为PNG格式的字节数据
    """
    import io
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def create_2dani_from_json(json_data, preview_image_path="", embed_binary=False):
    """
    将JSON格式转换为2dani.bmp数据
    """
    animation = json_data['animation']
    
    # 读取预览图片
    if preview_image_path and os.path.exists(preview_image_path):
        from PIL import Image
        img = Image.open(preview_image_path)
        width, height = img.size
        preview_data = write_png(img)
        preview_size = len(preview_data)
    else:
        # 如果没有预览图片，创建一个默认的1x1像素图片
        from PIL import Image
        img = Image.new('RGBA', (1, 1), (255, 255, 255, 0))
        width, height = 1, 1
        preview_data = write_png(img)
        preview_size = len(preview_data)
    
    # 构建2D动画数据
    data_buffer = bytearray()
    
    # 写入2danidata标记
    data_buffer.extend(struct.pack('<I', STR_2danidata))
    
    # 写入动画名称
    animation_name = animation.get('name', '')
    data_buffer.extend(write_auto_str(animation_name))
    
    # 写入关联图片 - 使用SZ类型（字符串数组）
    link_images = animation.get('link_images', [])
    var_buffer = bytearray()
    # 使用EXTSAVE_SZ_MASK64格式
    var_buffer.extend(struct.pack('<B', 0xC0 | len(link_images)))  # EXTSAVE_SZ_MASK64 + 元素数量
    
    for img_path in link_images:
        if embed_binary:
            # 读取图片文件并以二进制格式写入
            try:
                # 尝试读取图片文件
                if os.path.exists(img_path):
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                else:
                    # 如果找不到文件，尝试在当前目录下查找
                    base_name = os.path.basename(img_path)
                    if os.path.exists(base_name):
                        with open(base_name, 'rb') as f:
                            img_data = f.read()
                    else:
                        print(f"Warning: Image file not found: {img_path}")
                        img_data = b''
                
                if img_data:
                    # 写入二进制类型元素（使用EXTSAVE_BIN_DWORD格式）
                    var_buffer.extend(struct.pack('<B', 0xAD))  # EXTSAVE_BIN_DWORD
                    var_buffer.extend(struct.pack('<I', len(img_data)))
                    var_buffer.extend(img_data)
                else:
                    # 如果读取失败，回退到写入路径字符串
                    var_buffer.extend(struct.pack('<B', 0xB2))  # EXTSAVE_STR_WORD
                    gbox_unicode = write_gbox_unicode(img_path)
                    var_buffer.extend(struct.pack('<H', len(gbox_unicode)))
                    var_buffer.extend(gbox_unicode)
            except Exception as e:
                print(f"Error embedding image {img_path}: {e}")
                # 出错时回退到写入路径字符串
                var_buffer.extend(struct.pack('<B', 0xB2))  # EXTSAVE_STR_WORD
                gbox_unicode = write_gbox_unicode(img_path)
                var_buffer.extend(struct.pack('<H', len(gbox_unicode)))
                var_buffer.extend(gbox_unicode)
        else:
            # 直接使用原始路径，不进行清理
            # 写入字符串类型元素（使用EXTSAVE_STR_WORD格式）
            var_buffer.extend(struct.pack('<B', 0xB2))  # EXTSAVE_STR_WORD
            # 使用GBox的Unicode编码格式
            gbox_unicode = write_gbox_unicode(img_path)
            var_buffer.extend(struct.pack('<H', len(gbox_unicode)))
            var_buffer.extend(gbox_unicode)
    
    # 写入var
    data_buffer.extend(write_auto_var(var_buffer))
    
    # 写入kinds数据
    kinds = animation.get('kinds', [])
    for kind in kinds:
        kind_buffer = bytearray()
        kind_buffer.extend(struct.pack('<I', STR_2danikind))
        kind_buffer.extend(struct.pack('<B', 1))  # version
        
        # 写入kind名称
        kind_name = kind.get('name', 'Idle')
        kind_buffer.extend(write_auto_str(kind_name))
        
        # 写入循环标志
        loop = kind.get('loop', True)
        kind_buffer.extend(struct.pack('<B', 1 if loop else 0))
        
        # 写入最大帧时间
        max_frame_time = kind.get('max_frame_time', 0.1)
        kind_buffer.extend(struct.pack('<f', max_frame_time))
        
        # 写入显示矩形
        # 使用固定的显示矩形，确保动画可见
        kind_buffer.extend(struct.pack('<ffff', -100, -100, 100, 100))
        
        # 写入点矩形（为空）
        kind_buffer.extend(struct.pack('<B', 0))
        
        # 写入轨道数量
        tracks = kind.get('tracks', [])
        kind_buffer.extend(struct.pack('<H', len(tracks)))
        
        for track in tracks:
            # 计算图片的半宽和半高，用于轨道数据
            half_width = width / 2
            half_height = height / 2
            
            # 写入轨道数据
            track_buffer = bytearray()
            track_buffer.extend(struct.pack('<I', STR_2danitrack))
            track_buffer.extend(struct.pack('<B', 2))  # version
            
            # 写入轨道名称
            track_name = track.get('name', 'Main')
            track_buffer.extend(write_auto_str(track_name))
            
            # 写入图片索引
            img_index = track.get('img_index', 0)
            track_buffer.extend(struct.pack('<I', img_index))
            
            # 写入结束时间和循环时间
            end_time = track.get('end_time', 0.1)
            loop_time = track.get('loop_time', 0.1)
            track_buffer.extend(struct.pack('<f', end_time))
            track_buffer.extend(struct.pack('<f', loop_time))
            
            # 写入插值方式、循环模式、混合模式
            interpolation_kind = track.get('interpolation_kind', 1)
            loop_mode = track.get('loop_mode', 0)
            blend_mode = track.get('blend_mode', 1)
            track_buffer.extend(struct.pack('<B', interpolation_kind))
            track_buffer.extend(struct.pack('<B', loop_mode))
            track_buffer.extend(struct.pack('<B', blend_mode))
            
            # 写入关键帧数量、顶点数量、网格大小
            key_frames = track.get('key_frames', [])
            track_buffer.extend(struct.pack('<H', len(key_frames)))
            # 从轨道数据中获取顶点数量和网格大小
            vertex_count = track.get('vertex_count', 4)
            grid_w = track.get('grid_w', 1)
            grid_h = track.get('grid_h', 1)
            track_buffer.extend(struct.pack('<H', vertex_count))
            track_buffer.extend(struct.pack('<B', grid_w))
            track_buffer.extend(struct.pack('<B', grid_h))
            
            # 写入关键帧定义大小和数据
            key_size = 8  # G2DANIPT_KEY的大小
            track_buffer.extend(struct.pack('<B', key_size))
            
            for key_frame in key_frames:
                # 关键帧时间和标志
                time = key_frame.get('time', 0.0)
                flag = key_frame.get('flag', 0)
                track_buffer.extend(struct.pack('<f', time))
                track_buffer.extend(struct.pack('<I', flag))  # 标志
            
            # 写入关键帧数据大小和数据
            key_pt_size = 24  # G2DANIPT_TYPE的大小 (vec3 pos + vec2 uv + DWORD color = 12 + 8 + 4 = 24)
            track_buffer.extend(struct.pack('<B', key_pt_size))
            
            for key_frame in key_frames:
                vertices = key_frame.get('vertices', [])
                for vertex in vertices:
                    # 写入顶点数据
                    pos = vertex.get('position', [0, 0, 0])
                    track_buffer.extend(struct.pack('<fff', pos[0], pos[1], pos[2]))
                    
                    uv = vertex.get('uv', [0, 0])
                    track_buffer.extend(struct.pack('<ff', uv[0], uv[1]))
                    
                    color = vertex.get('color', W_COLOR)
                    track_buffer.extend(struct.pack('<I', color))
            
            # 写入结束标志
            track_buffer.extend(struct.pack('<B', 0))
            
            # 将轨道数据添加到kind数据
            kind_buffer.extend(track_buffer)
        
        # 写入kind结束标志
        kind_buffer.extend(struct.pack('<B', 0))
        
        # 将kind数据添加到主数据（使用AddEx格式）
        # AddEx格式：[flag(4字节)][datasize(4字节)][data]
        kind_size = len(kind_buffer)
        data_buffer.extend(struct.pack('<I', STR_2danikind))  # flag
        data_buffer.extend(struct.pack('<I', kind_size))  # datasize
        data_buffer.extend(kind_buffer)  # data
    
    # 写入文件末尾的标志和版本
    data_buffer.extend(struct.pack('<I', ANIFILE_FLAG))
    data_buffer.extend(struct.pack('<I', ANIFILE_VER))
    data_buffer.extend(struct.pack('<I', preview_size))  # 预览数据偏移量
    data_buffer.extend(struct.pack('<I', 0))  # 保留
    
    # 合并预览数据和动画数据
    final_data = preview_data + data_buffer
    
    return final_data

def create_2dani_from_image(image_path, width, height, center_x=None, center_y=None, embed_binary=False):
    """
    将图片转换为单帧动画格式
    """
    # 如果没有指定中心点，默认居中
    if center_x is None:
        center_x = width / 2
    if center_y is None:
        center_y = height / 2
    
    # 计算顶点位置，使图片居中
    half_width = width / 2
    half_height = height / 2
    
    # 获取图片文件名，并确保它是有效的
    img_name = os.path.basename(image_path)
    # 清理文件名，确保它不包含任何特殊字符
    img_name = ''.join(c for c in img_name if c.isalnum() or c in '_.-')
    
    # 构建JSON数据
    # 如果要嵌入二进制数据，需要提供完整路径以便读取文件
    # 如果不嵌入，只保留文件名以保持兼容性
    link_imgs = [image_path] if embed_binary else [img_name]
    
    json_data = {
        "animation": {
            "name": "animation",
            "link_images": link_imgs,
            "kinds": [
                {
                    "name": "std",
                    "loop": True,
                    "max_frame_time": 0.0,
                    "tracks": [
                        {
                            "name": "",
                            "img_index": 0,
                            "end_time": 0.0,
                            "loop_time": 0.0,
                            "interpolation_kind": 1,
                            "loop_mode": 1,
                            "blend_mode": 1,
                            "key_frames": [
                                {
                                    "time": 0.0,
                                    "flag": 0x00020000,
                                    "vertices": [
                                        {
                                            "position": [-center_x, -center_y, 0],
                                            "uv": [0, 0],
                                            "color": W_COLOR
                                        },
                                        {
                                            "position": [-center_x + width, -center_y, 0],
                                            "uv": [1, 0],
                                            "color": W_COLOR
                                        },
                                        {
                                            "position": [-center_x, -center_y + height, 0],
                                            "uv": [0, 1],
                                            "color": W_COLOR
                                        },
                                        {
                                            "position": [-center_x + width, -center_y + height, 0],
                                            "uv": [1, 1],
                                            "color": W_COLOR
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    # 转换为2dani格式，传递图片路径作为预览图片
    return create_2dani_from_json(json_data, image_path, embed_binary=embed_binary)
