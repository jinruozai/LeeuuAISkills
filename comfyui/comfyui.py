#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI Image Generation Client
Self-contained module for generating images via ComfyUI WebSocket API
"""

import websocket
import uuid
import json
import urllib.request
import urllib.error
import os
import io
import re
import time
import datetime
import logging
import sys
import subprocess
import platform
import tempfile
from PIL import Image

# Add gboxani lib to path
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gboxani_lib = os.path.join(current_dir, 'gboxani', 'lib')
    if os.path.exists(gboxani_lib) and gboxani_lib not in sys.path:
        sys.path.insert(0, gboxani_lib)
    from ani_parser import create_2dani_from_image
    from image_analyzer import analyze_image as _analyze_iso_image
except ImportError:
    create_2dani_from_image = None
    _analyze_iso_image = None

def _get_logger(name='comfyui'):
    logger = logging.getLogger(f'skill.{name}')
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

_logger = _get_logger()


def _parse_output_path(output):
    """
    分析输出路径
    
    Args:
        output: 输出路径（可以是目录或文件路径）
    
    Returns:
        tuple: (output_dir, output_filename)
    """
    if not output:
        return None, None
    
    # 支持的图片格式
    supported_formats = ['.png', '.jpg', '.jpeg', '.webp', '.2dani.bmp']
    has_valid_extension = any(output.lower().endswith(ext) for ext in supported_formats)
    
    if has_valid_extension:
        # 是文件路径
        output_dir = os.path.dirname(output)
        output_filename = os.path.basename(output)
    else:
        # 是目录路径
        output_dir = output
        output_filename = None
    
    return output_dir, output_filename

def _resize_image(image, width=None, height=None):
    """
    Resize image to specified dimensions
    
    Args:
        image: PIL Image object
        width: Target width (optional)
        height: Target height (optional)
        
    Returns:
        PIL Image object: Resized image
    """
    if width and height:
        _logger.info(f"Resizing image to {width}x{height}")
        return image.resize((width, height), Image.Resampling.LANCZOS)
    return image

def _save_as_2dani(image, output_path, width=None, height=None, center_x=None, center_y=None):
    """
    Save image as .2dani.bmp format with embedded binary
    
    Args:
        image: PIL Image object
        output_path: Target output path (must end with .2dani.bmp)
        width: Target width (optional)
        height: Target height (optional)
        center_x: Center point X coordinate (optional, only for .2dani.bmp)
        center_y: Center point Y coordinate (optional, only for .2dani.bmp)
        
    Returns:
        str: The actual saved path (either .2dani.bmp or fallback .png)
    """
    if create_2dani_from_image:
        try:
            # Create temp png
            temp_png = output_path + ".temp.png"
            image.save(temp_png)
            
            # Use provided dimensions or image dimensions
            target_width = width if width else image.width
            target_height = height if height else image.height
            
            _logger.info(f"Converting to 2dani.bmp with embedded binary...")
            ani_data = create_2dani_from_image(
                temp_png, 
                target_width, 
                target_height, 
                center_x, 
                center_y, 
                embed_binary=True
            )
            
            with open(output_path, 'wb') as f:
                f.write(ani_data)
            
            # Clean up
            if os.path.exists(temp_png):
                os.remove(temp_png)
                
            _logger.info(f"图像已保存(2dani): {output_path}")
            return output_path
        except Exception as e:
            _logger.error(f"Failed to convert to 2dani: {e}")
            # Fallback to saving original image as png if conversion fails
            fallback_path = output_path + ".png"
            image.save(fallback_path)
            _logger.info(f"Fallback saved: {fallback_path}")
            return fallback_path
    else:
        _logger.error("gboxani library not found, cannot convert to .2dani.bmp")
        # Fallback to saving original image as png
        fallback_path = output_path + ".png"
        image.save(fallback_path)
        return fallback_path

def _compute_iso_params(image, ix, iy, anialign=0):
    """
    通过菱形占地分析, 计算标准化后的 width, height, center_x, center_y。

    Args:
        image: PIL Image (RGBA)
        ix, iy: 占地格数 (如 4x4)
        anialign: 对齐模式 0=edge(建筑/树), 1=center(角色)

    Returns:
        (width, height, center_x, center_y, footprint) 或 None
    """
    if _analyze_iso_image is None:
        _logger.error("image_analyzer 不可用, 无法计算占地参数")
        return None

    # 保存临时图片供分析
    temp_png = os.path.join(tempfile.gettempdir(), f"_iso_analyze_{uuid.uuid4().hex[:8]}.png")
    try:
        image.save(temp_png)
        fit_type = 'center' if anialign == 1 else 'edge'
        result = _analyze_iso_image(temp_png, ix, iy, fit_type, standardize=False)
        if result is None:
            return None

        scale = result['scale']
        new_w = max(1, int(round(image.width * scale)))
        new_h = max(1, int(round(image.height * scale)))

        # 中心格在缩放后的坐标
        cx, cy = result['center']
        center_x = cx * scale
        center_y = cy * scale

        footprint = result['footprint']
        _logger.info(f"占地分析: {ix}x{iy} {fit_type}  缩放: {scale:.3f}  "
                     f"尺寸: {new_w}x{new_h}  中心: ({center_x:.1f},{center_y:.1f})")
        _logger.info(f"占地格子: {footprint}")

        return new_w, new_h, center_x, center_y, footprint
    finally:
        if os.path.exists(temp_png):
            os.remove(temp_png)


DEFAULT_SERVER = "nat.leeuu.com:60080"
DEFAULT_WORKFLOW = "z_image.json"

class ComfyUI:
    def __init__(self, server_addr=None):
        addr = server_addr or DEFAULT_SERVER
        if addr.startswith(('http://', 'https://', 'ws://', 'wss://')):
            match = re.match(r'^(?:http|https|ws|wss)://([^:/]+(?::\d+)?)$', addr)
            if match:
                self.server_address = match.group(1)
            else:
                self.server_address = addr.split('://', 1)[1]
        else:
            self.server_address = addr
        self.client_id = str(uuid.uuid4())
    
    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            _logger.error(f"HTTP错误: {e.code} - {e.reason}")
            raise

    def get_images(self, ws, prompt):
        _logger.info("正在提交工作流...")
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        _logger.info(f"等待图像生成，任务ID: {prompt_id}")
        
        output_images = {}
        current_node = ""
        img_received = False
        last_msg_time = time.time()
        no_msg_timeout = 15
        
        while True:
            try:
                out = ws.recv()
                last_msg_time = time.time()
                
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['prompt_id'] == prompt_id:
                            if data['node'] is None:
                                _logger.info("工作流执行完成!")
                                break
                            else:
                                current_node = data['node']
                                _logger.info(f"正在执行节点: {current_node}")
                else:
                    _logger.info(f"收到来自节点 '{current_node}' 的图像数据")
                    images_output = output_images.get(current_node, [])
                    images_output.append(out[8:])
                    output_images[current_node] = images_output
                    img_received = True
                    
                current_time = time.time()
                if img_received and (current_time - last_msg_time) > no_msg_timeout:
                    _logger.info(f"已超过 {no_msg_timeout} 秒没有新消息，认为工作流已完成")
                    break
                    
            except websocket.WebSocketTimeoutException as e:
                _logger.warning(f"WebSocket超时: {e}")
                if img_received:
                    break
                else:
                    raise
        
        return output_images

    def add_websocket_node(self, workflow_data):
        for node_id, node in workflow_data.items():
            if node.get("class_type") == "SaveImageWebsocket":
                return workflow_data
        
        vae_node_id = None
        save_node_input = None
        
        for node_id, node in workflow_data.items():
            if node.get("class_type") == "VAEDecode":
                vae_node_id = node_id
            elif node.get("class_type") == "SaveImage":
                if "inputs" in node and "images" in node["inputs"]:
                    save_node_input = node["inputs"]["images"]
        
        if save_node_input:
            input_source = save_node_input
        elif vae_node_id:
            input_source = [vae_node_id, 0]
        else:
            return workflow_data
        
        workflow_data["save_image_websocket_node"] = {
            "class_type": "SaveImageWebsocket",
            "inputs": {"images": input_source}
        }
        return workflow_data
    
    def generate_images(self, prompt_text=None, workflow_path=None, output=None,
                        width=None, height=None, center_x=None, center_y=None,
                        ix=None, iy=None, anialign=0):
        """
        生成图像并返回保存的文件路径列表

        Args:
            prompt_text: 提示词文本
            workflow_path: 工作流文件名或路径
            output: 输出目录或文件路径（可选）
            width: Target width (optional)
            height: Target height (optional)
            center_x: Center point X coordinate (optional, only for .2dani.bmp)
            center_y: Center point Y coordinate (optional, only for .2dani.bmp)
            ix: 菱形占地 x 格数 (optional, 用于自动计算尺寸和中心点)
            iy: 菱形占地 y 格数 (optional, 用于自动计算尺寸和中心点)
            anialign: 对齐模式 0=edge(建筑/树), 1=center(角色) (default: 0)
        
        Returns:
            保存的图像路径列表
        """
        # 分析输出路径
        output_dir, output_filename = _parse_output_path(output)
        
        if output_dir is None:
            temp_dir = os.path.join(tempfile.gettempdir(), "comfyui_images")
            os.makedirs(temp_dir, exist_ok=True)
            output_dir = temp_dir
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        workflow_file = None
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        
        if workflow_path:
            if os.path.isabs(workflow_path) and os.path.exists(workflow_path):
                workflow_file = workflow_path
            else:
                skill_workflow = os.path.join(skill_dir, "workflows", workflow_path)
                if os.path.exists(skill_workflow):
                    workflow_file = skill_workflow
                elif not workflow_path.endswith('.json'):
                    skill_workflow = os.path.join(skill_dir, "workflows", f"{workflow_path}.json")
                    if os.path.exists(skill_workflow):
                        workflow_file = skill_workflow
        
        if not workflow_file:
            workflow_file = os.path.join(skill_dir, "workflows", DEFAULT_WORKFLOW)
        
        _logger.info(f"使用工作流文件: {workflow_file}")
        
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        if prompt_text:
            prompt_node = None
            for node_id, node in workflow_data.items():
                if node.get("class_type") == "CLIPTextEncode" and "inputs" in node and "text" in node["inputs"]:
                    if not prompt_node or node_id == "6":
                        prompt_node = node_id
            
            if prompt_node:
                workflow_data[prompt_node]["inputs"]["text"] = prompt_text
                _logger.info(f"提示词: {prompt_text}")
        
        workflow_data = self.add_websocket_node(workflow_data)
        
        _logger.info(f"连接WebSocket: ws://{self.server_address}/ws?clientId={self.client_id}")
        ws = websocket.WebSocket()
        ws.settimeout(300)
        
        saved_paths = []
        
        try:
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
            images = self.get_images(ws, workflow_data)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            image_count = 0
            
            for node_id, image_list in images.items():
                for i, image_data in enumerate(image_list):
                    try:
                        image = Image.open(io.BytesIO(image_data))
                        
                        # 检查是否提供了输出文件名
                        if output_filename and image_count == 0:
                            # 使用用户指定的文件名（已在_parse_output_path中校验过后缀）
                            output_name = output_filename
                        else:
                            # 使用默认命名方式
                            output_name = f"comfyui_{timestamp}_{unique_id}_{image_count}.png"
                        
                        output_path = os.path.join(output_dir, output_name)
                        
                        # Check if output is .2dani.bmp
                        is_2dani = output_name.lower().endswith('.2dani.bmp')
                        
                        # 调整图片尺寸（仅对非2dani.bmp格式）
                        if not is_2dani:
                            image = _resize_image(image, width, height)
                        
                        if is_2dani:
                            # 如果没传 width/height 但传了 ix/iy, 用占地分析自动计算
                            _w, _h, _cx, _cy = width, height, center_x, center_y
                            if _w is None and _h is None and ix is not None and iy is not None:
                                iso = _compute_iso_params(image, ix, iy, anialign)
                                if iso is not None:
                                    _w, _h, _cx, _cy = iso[0], iso[1], iso[2], iso[3]
                            _logger.info(f"2dani参数: width={_w} height={_h} center_x={_cx} center_y={_cy}")
                            saved_path = _save_as_2dani(image, output_path, _w, _h, _cx, _cy)
                            saved_paths.append(saved_path)
                        else:
                            image.save(output_path)
                            saved_paths.append(output_path)
                            _logger.info(f"图像已保存: {output_path}")
                            
                        image_count += 1
                    except Exception as e:
                        _logger.error(f"保存图像失败: {e}")
            
            _logger.info(f"成功生成 {image_count} 张图像")
            
            if saved_paths:
                try:
                    system = platform.system()
                    first_image = saved_paths[0]
                    if system == 'Darwin':
                        subprocess.run(['open', first_image], check=True)
                    elif system == 'Windows':
                        os.startfile(first_image)
                    elif system == 'Linux':
                        subprocess.run(['xdg-open', first_image], check=True)
                except Exception:
                    pass
                    
        finally:
            try:
                ws.close()
            except:
                pass
        
        return saved_paths


def generate_image(prompt, server="http://nat.leeuu.com:60080", workflow=None, output=None,
                   width=None, height=None, center_x=None, center_y=None,
                   ix=None, iy=None, anialign=0):
    """
    便捷函数：生成单张图片

    Args:
        prompt: 图片描述
        server: ComfyUI服务器地址
        workflow: 工作流文件名（可选）
        output: 输出目录或文件路径（可选）
        width: Target width (optional)
        height: Target height (optional)
        center_x: Center point X coordinate (optional, only for .2dani.bmp)
        center_y: Center point Y coordinate (optional, only for .2dani.bmp)
        ix: 菱形占地 x 格数 (optional)
        iy: 菱形占地 y 格数 (optional)
        anialign: 对齐模式 0=edge, 1=center (default: 0)

    Returns:
        生成的图片路径列表
    """
    comfy = ComfyUI(server)
    return comfy.generate_images(prompt, workflow, output, width, height,
                                center_x, center_y, ix, iy, anialign)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate AI images using ComfyUI')
    parser.add_argument('prompt', help='Image description prompt')
    parser.add_argument('--server', default='http://nat.leeuu.com:60080', help='ComfyUI server address')
    parser.add_argument('--workflow', default='z_image.json', help='Workflow filename')
    parser.add_argument('--output', help='Output directory or file path')
    parser.add_argument('--width', type=int, help='Target width')
    parser.add_argument('--height', type=int, help='Target height')
    parser.add_argument('--center-x', type=float, help='Center point X coordinate (only for .2dani.bmp)')
    parser.add_argument('--center-y', type=float, help='Center point Y coordinate (only for .2dani.bmp)')
    parser.add_argument('--ix', type=int, help='菱形占地 x 格数 (自动计算尺寸/中心点)')
    parser.add_argument('--iy', type=int, help='菱形占地 y 格数 (自动计算尺寸/中心点)')
    parser.add_argument('--anialign', type=int, default=0, help='对齐模式 0=edge(建筑) 1=center(角色)')

    args = parser.parse_args()
    paths = generate_image(
        prompt=args.prompt,
        server=args.server,
        workflow=args.workflow,
        output=args.output,
        width=args.width,
        height=args.height,
        center_x=args.center_x,
        center_y=args.center_y,
        ix=args.ix,
        iy=args.iy,
        anialign=args.anialign
    )
    print(f'Generated images: {paths}')
