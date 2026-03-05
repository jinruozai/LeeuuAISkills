#!/usr/bin/env python3
import os
import sys
import argparse

# 添加python目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# 导入模块
from ani_parser import (
    parse_2dani_to_json,
    create_2dani_from_json,
    create_2dani_from_image
)

def main():
    """
    GBox 2D动画转换工具
    """
    parser = argparse.ArgumentParser(description='GBox 2D动画转换工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # to_json命令：将2dani文件转换为JSON格式
    parser_to_json = subparsers.add_parser('to_json', help='将2dani文件转换为JSON格式')
    parser_to_json.add_argument('input_file', help='输入的2dani文件路径')
    parser_to_json.add_argument('output_dir', help='输出目录')
    parser_to_json.add_argument('--base-name', default='animation', help='基础文件名')
    
    # from_json命令：将JSON文件转换为2dani格式
    parser_from_json = subparsers.add_parser('from_json', help='将JSON文件转换为2dani格式')
    parser_from_json.add_argument('input_file', help='输入的JSON文件路径')
    parser_from_json.add_argument('output_file', help='输出的2dani文件路径')
    parser_from_json.add_argument('--embed', action='store_true', help='将图片以二进制格式嵌入到动画文件中')
    
    # from_image命令：将图片转换为2dani格式
    parser_from_image = subparsers.add_parser('from_image', help='将图片转换为2dani格式')
    parser_from_image.add_argument('input_file', help='输入的图片文件路径')
    parser_from_image.add_argument('output_file', help='输出的2dani文件路径')
    parser_from_image.add_argument('--width', type=int, default=200, help='动画宽度')
    parser_from_image.add_argument('--height', type=int, default=200, help='动画高度')
    parser_from_image.add_argument('--center-x', type=float, help='中心点X坐标')
    parser_from_image.add_argument('--center-y', type=float, help='中心点Y坐标')
    parser_from_image.add_argument('--embed', action='store_true', help='将图片以二进制格式嵌入到动画文件中')
    
    args = parser.parse_args()
    
    if args.command == 'to_json':
        # 将2dani文件转换为JSON格式
        try:
            with open(args.input_file, 'rb') as f:
                ani_data = f.read()
            
            result = parse_2dani_to_json(ani_data, args.output_dir, args.base_name)
            
            # 保存JSON文件
            json_path = os.path.join(args.output_dir, f'{args.base_name}.json')
            import json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 成功转换为JSON: {json_path}")
            print(f"  动画名称: {result['animation']['name']}")
            print(f"  关联图片: {result['animation']['link_images']}")
            print(f"  动画种类: {len(result['animation']['kinds'])}")
            
        except Exception as e:
            print(f"✗ 转换失败: {e}")
            return 1
    
    elif args.command == 'from_json':
        # 将JSON文件转换为2dani格式
        try:
            import json
            with open(args.input_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            ani_data = create_2dani_from_json(json_data, embed_binary=args.embed)
            
            with open(args.output_file, 'wb') as f:
                f.write(ani_data)
            
            print(f"✓ 成功转换为2dani: {args.output_file}")
            print(f"  文件大小: {len(ani_data)} bytes")
            
        except Exception as e:
            print(f"✗ 转换失败: {e}")
            return 1
    
    elif args.command == 'from_image':
        # 将图片转换为2dani格式
        try:
            ani_data = create_2dani_from_image(
                args.input_file,
                args.width,
                args.height,
                args.center_x,
                args.center_y,
                embed_binary=args.embed
            )
            
            with open(args.output_file, 'wb') as f:
                f.write(ani_data)
            
            print(f"✓ 成功转换为2dani: {args.output_file}")
            print(f"  文件大小: {len(ani_data)} bytes")
            print(f"  动画尺寸: {args.width}x{args.height}")
            
        except Exception as e:
            print(f"✗ 转换失败: {e}")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
