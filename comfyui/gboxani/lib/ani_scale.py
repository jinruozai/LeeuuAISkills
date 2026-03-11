#!/usr/bin/env python3
"""
GBox 2D动画缩放工具

提供两个核心功能：
1. 按比例缩放动画的所有顶点
2. 计算缩放值并适配到目标尺寸
"""

def scale_animation(animation_data, scale_factor):
    """
    缩放动画，把所有kind里所有track的顶点都以原点为中心缩放
    
    Args:
        animation_data: 动画数据（JSON格式）
        scale_factor: 缩放因子
    
    Returns:
        缩放后的动画数据
    """
    # 遍历所有kind
    for kind in animation_data['animation'].get('kinds', []):
        # 遍历所有track
        for track in kind.get('tracks', []):
            # 遍历所有关键帧
            for key_frame in track.get('key_frames', []):
                # 遍历所有顶点
                for vertex in key_frame.get('vertices', []):
                    # 缩放顶点位置
                    pos = vertex.get('position', [0, 0, 0])
                    scaled_pos = [pos[0] * scale_factor, pos[1] * scale_factor, pos[2] * scale_factor]
                    vertex['position'] = scaled_pos
    
    return animation_data

def calculate_aabb(animation_data):
    """
    计算动画的AABB边界框
    
    Args:
        animation_data: 动画数据（JSON格式）
    
    Returns:
        (min_x, min_y, max_x, max_y)
    """
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    # 获取第一个kind
    kinds = animation_data['animation'].get('kinds', [])
    if not kinds:
        return (0, 0, 0, 0)
    
    first_kind = kinds[0]
    
    # 遍历第一个kind的所有track
    for track in first_kind.get('tracks', []):
        # 遍历所有关键帧
        for key_frame in track.get('key_frames', []):
            # 遍历所有顶点
            for vertex in key_frame.get('vertices', []):
                pos = vertex.get('position', [0, 0, 0])
                x, y = pos[0], pos[1]
                
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    
    # 如果没有顶点数据，返回默认值
    if min_x == float('inf'):
        return (0, 0, 0, 0)
    
    return (min_x, min_y, max_x, max_y)

def scale_animation_to_fit(animation_data, target_width, target_height):
    """
    缩放动画适配目标尺寸
    
    1. 解析出第一个kind的所有顶点，计算AABB
    2. 根据目标尺寸，计算一个缩放值
    3. 调用scale_animation，缩放所有动画
    
    Args:
        animation_data: 动画数据（JSON格式）
        target_width: 目标宽度
        target_height: 目标高度
    
    Returns:
        缩放后的动画数据
    """
    # 计算AABB
    min_x, min_y, max_x, max_y = calculate_aabb(animation_data)
    
    # 计算当前尺寸
    current_width = max_x - min_x
    current_height = max_y - min_y
    
    # 计算缩放因子
    if current_width == 0 or current_height == 0:
        # 如果当前尺寸为0，使用默认缩放因子
        scale_factor = 1.0
    else:
        # 计算宽度和高度的缩放因子
        scale_x = target_width / current_width
        scale_y = target_height / current_height
        # 使用较小的缩放因子，确保完全适配
        scale_factor = min(scale_x, scale_y)
    
    # 缩放动画
    return scale_animation(animation_data, scale_factor)