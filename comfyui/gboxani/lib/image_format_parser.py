import struct
import io
from PIL import Image

# 定义 JGEIMGFLAG 常量
JGEIMGFLAG = 0xF6BDCA96

def detect_image_format(data):
    """
    检测图像格式，基于文件头特征
    优先检查ALE格式，然后按照JGEIMGFLAG -> JPEG -> PNG -> GIF -> 内部格式的顺序
    """
    if not data:
        return None
    
    # 优先检查文件头
    if data.startswith(b'\x89PNG'):
        return 'png'
    if data.startswith(b'\xff\xd8'):
        return 'jpeg'
    if data.startswith(b'GIF89a') or data.startswith(b'GIF87a'):
        return 'gif'
    
    # 检查ALE格式
    ale_pos = data.find(b'ALE')
    if ale_pos != -1 and ale_pos + 3 <= len(data):
        return 'ale'
    ale_pos = data.find(b'AEX')
    if ale_pos != -1 and ale_pos + 3 <= len(data):
        return 'ale'
    
    # 检查JGEIMGFLAG格式（在整个数据中搜索）
    for i in range(len(data) - 4):
        flag = struct.unpack('<I', data[i:i+4])[0]
        if flag == JGEIMGFLAG:
            # 检查是否有足够的数据
            if i + 32 <= len(data):
                # 读取JGEIMGFLAG头，检查版本和偏移量
                try:
                    ver = struct.unpack('<I', data[i+4:i+8])[0]
                    width = struct.unpack('<I', data[i+8:i+12])[0]
                    height = struct.unpack('<I', data[i+12:i+16])[0]
                    jpgoffset = struct.unpack('<I', data[i+16:i+20])[0]
                    jpglen = struct.unpack('<I', data[i+20:i+24])[0]
                    gifoffset = struct.unpack('<I', data[i+24:i+28])[0]
                    giflen = struct.unpack('<I', data[i+28:i+32])[0]
                    
                    # 检查版本是否为1
                    if ver == 1:
                        # 检查宽度和高度是否合理
                        if 0 < width <= 2048 and 0 < height <= 2048:
                            # 检查偏移量和长度是否合理
                            if (jpgoffset + jpglen <= len(data) - i and 
                                gifoffset + giflen <= len(data) - i and 
                                jpgoffset >= 0 and 
                                gifoffset >= 0 and 
                                jpglen > 0 and 
                                giflen > 0):
                                return 'jgeimg'
                except:
                    pass
    
    # 检查JPEG格式（优先于GIF，因为GIF可能是小的无效图像）
    jpeg_pos = data.find(b'\xff\xd8')
    if jpeg_pos != -1 and jpeg_pos + 2 <= len(data):
        return 'jpeg'
    
    # 检查PNG格式
    png_pos = data.find(b'\x89PNG')
    if png_pos != -1 and png_pos + 4 <= len(data):
        return 'png'
    
    # 检查GIF格式
    gif_pos = data.find(b'GIF89a')
    if gif_pos != -1 and gif_pos + 6 <= len(data):
        # 检查GIF图像的宽度和高度是否合理
        width = struct.unpack('<H', data[gif_pos+6:gif_pos+8])[0]
        height = struct.unpack('<H', data[gif_pos+8:gif_pos+10])[0]
        # 如果宽度和高度都大于2像素，则认为是有效的GIF图像
        if width > 2 and height > 2:
            return 'gif'
    gif_pos = data.find(b'GIF87a')
    if gif_pos != -1 and gif_pos + 5 <= len(data):
        # 检查GIF图像的宽度和高度是否合理
        width = struct.unpack('<H', data[gif_pos+6:gif_pos+8])[0]
        height = struct.unpack('<H', data[gif_pos+8:gif_pos+10])[0]
        # 如果宽度和高度都大于2像素，则认为是有效的GIF图像
        if width > 2 and height > 2:
            return 'gif'
    
    # 检查内部IMG1格式
    for i in range(len(data) - 4):
        if struct.unpack('I', data[i:i+4])[0] == 0x494D4731:  # FLAG_IMG1
            return 'img1'
    
    return None

def find_image_data(data):
    """
    在二进制数据中查找图像数据的起始位置
    """
    if not data:
        return None, None
    
    # 优先检查文件头
    if data.startswith(b'\x89PNG'):
        return 'png', 0
    if data.startswith(b'\xff\xd8'):
        return 'jpeg', 0
    if data.startswith(b'GIF89a') or data.startswith(b'GIF87a'):
        return 'gif', 0
    
    # 查找ALE格式
    ale_pos = data.find(b'ALE')
    if ale_pos != -1:
        return 'ale', ale_pos
    ale_pos = data.find(b'AEX')
    if ale_pos != -1:
        return 'ale', ale_pos
    
    # 查找JGEIMGFLAG格式（在整个数据中搜索）
    for i in range(len(data) - 4):
        flag = struct.unpack('<I', data[i:i+4])[0]
        if flag == JGEIMGFLAG:
            # 检查是否有足够的数据
            if i + 32 <= len(data):
                # 读取JGEIMGFLAG头，检查版本和偏移量
                try:
                    ver = struct.unpack('<I', data[i+4:i+8])[0]
                    width = struct.unpack('<I', data[i+8:i+12])[0]
                    height = struct.unpack('<I', data[i+12:i+16])[0]
                    jpgoffset = struct.unpack('<I', data[i+16:i+20])[0]
                    jpglen = struct.unpack('<I', data[i+20:i+24])[0]
                    gifoffset = struct.unpack('<I', data[i+24:i+28])[0]
                    giflen = struct.unpack('<I', data[i+28:i+32])[0]
                    
                    # 检查版本是否为1
                    if ver == 1:
                        # 检查宽度和高度是否合理
                        if 0 < width <= 2048 and 0 < height <= 2048:
                            # 检查偏移量和长度是否合理
                            if (jpgoffset + jpglen <= len(data) - i and 
                                gifoffset + giflen <= len(data) - i and 
                                jpgoffset >= 0 and 
                                gifoffset >= 0 and 
                                jpglen > 0 and 
                                giflen > 0):
                                return 'jgeimg', i
                except:
                    pass
    
    # 查找JPEG格式（优先于GIF，因为GIF可能是小的无效图像）
    jpeg_pos = data.find(b'\xff\xd8')
    if jpeg_pos != -1:
        return 'jpeg', jpeg_pos
    
    # 查找PNG格式
    png_pos = data.find(b'\x89PNG')
    if png_pos != -1:
        return 'png', png_pos
    
    # 查找GIF格式
    gif_pos = data.find(b'GIF89a')
    if gif_pos != -1:
        # 检查GIF图像的宽度和高度是否合理
        if gif_pos + 6 <= len(data):
            # 读取GIF的宽度和高度
            width = struct.unpack('<H', data[gif_pos+6:gif_pos+8])[0]
            height = struct.unpack('<H', data[gif_pos+8:gif_pos+10])[0]
            # 如果宽度和高度都大于2像素，则认为是有效的GIF图像
            if width > 2 and height > 2:
                return 'gif', gif_pos
    gif_pos = data.find(b'GIF87a')
    if gif_pos != -1:
        # 检查GIF图像的宽度和高度是否合理
        if gif_pos + 6 <= len(data):
            # 读取GIF的宽度和高度
            width = struct.unpack('<H', data[gif_pos+6:gif_pos+8])[0]
            height = struct.unpack('<H', data[gif_pos+8:gif_pos+10])[0]
            # 如果宽度和高度都大于2像素，则认为是有效的GIF图像
            if width > 2 and height > 2:
                return 'gif', gif_pos
    
    # 查找内部IMG1格式
    for i in range(len(data) - 4):
        if struct.unpack('I', data[i:i+4])[0] == 0x494D4731:  # FLAG_IMG1
            return 'img1', i
    
    return None, None

def parse_image_data(data):
    """
    解析图像数据，根据格式返回对应的图像对象
    """
    # 找到图像数据的起始位置
    format, pos = find_image_data(data)
    
    if format is None:
        raise ValueError("No image data found")
    
    # 从找到的位置开始解析图像数据
    image_data = data[pos:]
    
    if format == 'gif':
        return parse_gif(image_data)
    elif format == 'png':
        return parse_png(image_data)
    elif format == 'jpeg':
        return parse_jpeg(image_data)
    elif format == 'ale':
        return parse_ale(image_data)
    elif format == 'img1':
        return parse_img1(image_data)
    elif format == 'jgeimg':
        return parse_jgeimg(image_data)
    else:
        raise ValueError(f"Unknown image format: {format}")

def parse_gif(data):
    """
    解析GIF格式
    """
    try:
        img = Image.open(io.BytesIO(data))
        return img
    except Exception as e:
        raise ValueError(f"Failed to parse GIF: {e}")

def parse_png(data):
    """
    解析PNG格式
    """
    try:
        img = Image.open(io.BytesIO(data))
        return img
    except Exception as e:
        raise ValueError(f"Failed to parse PNG: {e}")

def parse_jpeg(data):
    """
    解析JPEG格式
    """
    try:
        img = Image.open(io.BytesIO(data))
        return img
    except Exception as e:
        raise ValueError(f"Failed to parse JPEG: {e}")

def parse_ale(data):
    """
    解析ALE格式
    """
    try:
        from ale_parser import ALEParser
        parser = ALEParser(data)
        img = parser.to_pil_image()
        return img
    except Exception as e:
        raise ValueError(f"Failed to parse ALE: {e}")

def parse_img1(data):
    """
    解析内部IMG1格式
    """
    try:
        # 跳过文件头
        offset = 4  # FLAG_IMG1
        
        # 读取总大小
        total_size = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        
        # 读取图像类型
        kind = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        
        # 读取宽高
        width = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        height = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        
        # 根据类型读取像素数据
        if kind == 0x0040:  # IMG_KIND_RGBA
            byte_per_pixel = 4
            mode = 'RGBA'
        elif kind == 0x0030:  # IMG_KIND_RGB
            byte_per_pixel = 3
            mode = 'RGB'
        elif kind == 0x0011:  # IMG_KIND_GRAY
            byte_per_pixel = 1
            mode = 'L'
        elif kind == 0x0021:  # IMG_KIND_565
            byte_per_pixel = 2
            mode = 'RGB'  # 需要转换
        else:
            raise ValueError(f"Unsupported IMG1 kind: {kind}")
        
        # 计算每行字节数
        byte_per_line = ((width * byte_per_pixel) + 3) & ~3
        
        # 读取像素数据
        pixel_data = data[offset:offset + byte_per_line * height]
        
        if kind == 0x0021:  # IMG_KIND_565
            # 转换565格式到RGB
            rgb_data = b''
            for i in range(0, len(pixel_data), 2):
                if i + 1 < len(pixel_data):
                    val = struct.unpack('H', pixel_data[i:i+2])[0]
                    r = ((val >> 11) & 0x1F) << 3
                    g = ((val >> 5) & 0x3F) << 2
                    b = (val & 0x1F) << 3
                    rgb_data += struct.pack('BBB', r, g, b)
            img = Image.frombytes('RGB', (width, height), rgb_data)
        else:
            img = Image.frombytes(mode, (width, height), pixel_data, 'raw', mode, 0, 1)
        
        return img
    except Exception as e:
        raise ValueError(f"Failed to parse IMG1: {e}")

def parse_jgeimg(data):
    """
    解析JGEIMGFLAG格式
    使用mask的黑色作为透明通道，将原图和mask合成一张带alpha通道的图像
    """
    try:
        # 读取JGEIMGFLAG头
        class JGEHead:
            def __init__(self, data):
                self.ver = struct.unpack('<I', data[4:8])[0]
                self.width = struct.unpack('<I', data[8:12])[0]
                self.height = struct.unpack('<I', data[12:16])[0]
                self.jpgoffset = struct.unpack('<I', data[16:20])[0]
                self.jpglen = struct.unpack('<I', data[20:24])[0]
                self.gifoffset = struct.unpack('<I', data[24:28])[0]
                self.giflen = struct.unpack('<I', data[28:32])[0]
        
        head = JGEHead(data)
        if head.ver != 1:
            raise ValueError("Invalid JGEIMGFLAG version")
        
        # 解析JPEG数据（原图）- 偏移量是相对于JGEIMGFLAG头的开始
        jpeg_data = data[head.jpgoffset:head.jpgoffset + head.jpglen]
        jpeg_img = Image.open(io.BytesIO(jpeg_data))
        
        # 解析GIF数据（mask）- 偏移量是相对于JGEIMGFLAG头的开始
        gif_data = data[head.gifoffset:head.gifoffset + head.giflen]
        mask_img = Image.open(io.BytesIO(gif_data))
        
        # 确保图像大小一致
        if jpeg_img.size != (head.width, head.height) or mask_img.size != (head.width, head.height):
            # 调整mask图像大小以匹配原图
            mask_img = mask_img.resize(jpeg_img.size, Image.LANCZOS)
        
        # 将原图转换为RGB模式
        if jpeg_img.mode != 'RGB':
            jpeg_img = jpeg_img.convert('RGB')
        
        # 处理mask图像，创建alpha通道
        # 无论mask是什么模式，都转换为灰度模式
        if mask_img.mode != 'L':
            mask_img = mask_img.convert('L')
        
        # 创建alpha通道：黑色为透明，其他颜色为不透明
        alpha = Image.new('L', mask_img.size, 0)
        mask_pixels = mask_img.load()
        alpha_pixels = alpha.load()
        
        for y in range(mask_img.height):
            for x in range(mask_img.width):
                # 黑色像素（值为0）设为透明（alpha 0），其他设为不透明（alpha 255）
                if mask_pixels[x, y] == 0:
                    alpha_pixels[x, y] = 0
                else:
                    alpha_pixels[x, y] = 255
        
        # 创建一个新的RGBA图像并应用alpha通道
        result_img = jpeg_img.copy()
        result_img.putalpha(alpha)
        
        return result_img
    except Exception as e:
        raise ValueError(f"Failed to parse JGEIMGFLAG: {e}")

def save_image(img, output_path):
    """
    保存图像到文件
    """
    try:
        img.save(output_path)
        return True
    except Exception as e:
        print(f"Failed to save image: {e}")
        return False
