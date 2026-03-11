#!/usr/bin/env python3
import os
import sys
import argparse
import json

# 添加python目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# 导入模块
from ani_parser import (
    parse_2dani_to_json,
    parse_2dani_to_json_with_embedded_images,
    create_2dani_from_json,
    create_2dani_from_image
)
from ani_scale import (
    scale_animation,
    scale_animation_to_fit
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
    
    # scale命令：按比例缩放动画
    parser_scale = subparsers.add_parser('scale', help='按比例缩放动画')
    parser_scale.add_argument('input_files', nargs='+', help='输入的2dani文件路径（可多个）')
    parser_scale.add_argument('--scale', type=float, required=True, help='缩放因子')
    parser_scale.add_argument('--output', help='输出文件路径，默认为覆盖原文件')
    parser_scale.add_argument('--output-dir', help='输出目录，默认为输入文件所在目录')
    
    # fit命令：按目标尺寸适配缩放动画
    parser_fit = subparsers.add_parser('fit', help='按目标尺寸适配缩放动画')
    parser_fit.add_argument('input_files', nargs='+', help='输入的2dani文件路径（可多个）')
    parser_fit.add_argument('--width', type=int, required=True, help='目标宽度')
    parser_fit.add_argument('--height', type=int, required=True, help='目标高度')
    parser_fit.add_argument('--output', help='输出文件路径，默认为覆盖原文件')
    parser_fit.add_argument('--output-dir', help='输出目录，默认为输入文件所在目录')
    
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
    
    elif args.command == 'scale':
        # 按比例缩放动画
        try:
            for input_file in args.input_files:
                # 读取2dani文件
                with open(input_file, 'rb') as f:
                    ani_data = f.read()
                
                # 转换为JSON
                json_data = parse_2dani_to_json_with_embedded_images(ani_data)
                
                # 输出数据的所有键
                print(f"json_data 的所有键: {list(json_data["animation"]["link_images"])}")
  
                # 缩放动画
                scaled_data = scale_animation(json_data, args.scale)
                
                
                # 转换回2dani，传递原始文件作为预览图片
                scaled_ani_data = create_2dani_from_json(scaled_data, preview_image_path=input_file,embed_binary=True)
                
                # 确定输出路径
                if args.output:
                    output_file = args.output
                    # 确保输出目录存在
                    output_dir = os.path.dirname(output_file)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                elif args.output_dir:
                    output_dir = args.output_dir
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, os.path.basename(input_file))
                else:
                    # 直接覆盖原文件
                    output_file = input_file
                
                # 保存文件
                with open(output_file, 'wb') as f:
                    f.write(scaled_ani_data)
                
                print(f"✓ 成功缩放动画: {input_file} → {output_file}")
                print(f"  缩放因子: {args.scale}")
                print(f"  文件大小: {len(scaled_ani_data)} bytes")
            
        except Exception as e:
            print(f"✗ 缩放失败: {e}")
            return 1
    
    elif args.command == 'fit':
        # 按目标尺寸适配缩放动画
        try:
            for input_file in args.input_files:
                # 读取2dani文件
                with open(input_file, 'rb') as f:
                    ani_data = f.read()
                
                # 转换为JSON
                json_data = parse_2dani_to_json(ani_data)
                
                # 缩放动画以适配目标尺寸
                scaled_data = scale_animation_to_fit(json_data, args.width, args.height)
                
                # 转换回2dani，传递原始文件作为预览图片
                scaled_ani_data = create_2dani_from_json(scaled_data, preview_image_path=input_file)
                
                # 确定输出路径
                if args.output:
                    output_file = args.output
                    # 确保输出目录存在
                    output_dir = os.path.dirname(output_file)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                elif args.output_dir:
                    output_dir = args.output_dir
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, os.path.basename(input_file))
                else:
                    # 直接覆盖原文件
                    output_file = input_file
                
                # 保存文件
                with open(output_file, 'wb') as f:
                    f.write(scaled_ani_data)
                
                print(f"✓ 成功适配缩放动画: {input_file} → {output_file}")
                print(f"  目标尺寸: {args.width}x{args.height}")
                print(f"  文件大小: {len(scaled_ani_data)} bytes")
            
        except Exception as e:
            print(f"✗ 适配缩放失败: {e}")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
