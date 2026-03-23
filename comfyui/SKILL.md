---
name: "comfyui"
description: "Generate AI images using ComfyUI. Invoke when user wants to create images, generate pictures, or needs visual content from text descriptions."
---

# ComfyUI Image Generation Skill

This skill generates AI images using ComfyUI server. It is self-contained with all code and workflows included.

## Prerequisites

- ComfyUI server running (default: `http://nat.leeuu.com:60080`)
- Python dependencies: `websocket-client`, `Pillow`

Install dependencies:
```bash
pip install websocket-client Pillow
```

## Usage

Execute command line to generate images:

```bash
# Basic usage
python comfyui.py "<IMAGE_DESCRIPTION>"

# With custom parameters
python comfyui.py "<IMAGE_DESCRIPTION>" --workflow flux_schnell_checkpoint.json --output <OUTPUT_PATH>

# Examples
python comfyui.py "A beautiful sunset" --output sunset.jpg
python comfyui.py "Mountain landscape" --output /path/to/save
python comfyui.py "Beach scene" --output /path/to/save/beach_photo.png
```

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `z_image.json` | Z-Image model, fast (~30s) |
| `flux_schnell_checkpoint.json` | Flux Schnell model |
| `sd_base.json` | Stable Diffusion base |
| `z_image_blindbox.json` | Z-Image model for "盲盒世界" game |

## 盲盒世界游戏专用功能

### 工作流
- **`z_image_blindbox.json`**: 专为《盲盒世界》游戏设计的工作流，支持生成等距视角的角色和建筑

### 提示词模板

#### 角色盲盒提示词
- **文件**: `character_prompts.md`
- **包含**: 风格提示词（固定）、视角提示词（固定）、具体角色提示词（可替换）
- **使用**: 替换具体角色部分，保持风格和视角不变

#### 建筑盲盒提示词
- **文件**: `building_prompts.md`
- **包含**: 建筑风格提示词（固定）、视角提示词（固定）、具体建筑提示词（可替换）
- **使用**: 替换具体建筑部分，保持风格和视角不变

### 生成示例

```bash
# 生成角色盲盒
python comfyui.py "[风格提示词] [视角提示词] [具体角色提示词]" --workflow z_image_blindbox.json

# 生成建筑盲盒
python comfyui.py "[建筑风格提示词] [视角提示词] [具体建筑提示词]" --workflow z_image_blindbox.json
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | required | Image description |
| `server` | str | `http://nat.leeuu.com:60080` | ComfyUI server address |
| `workflow` | str | `z_image.json` | Workflow filename |
| `output` | str | temp dir | Output directory or file path |
| `width` | int | None | Target width (for image resizing or animation dimensions) |
| `height` | int | None | Target height (for image resizing or animation dimensions) |
| `center-x` | float | None | Center point X coordinate (only for .2dani.bmp format, relative to top-left corner) |
| `center-y` | float | None | Center point Y coordinate (only for .2dani.bmp format, relative to top-left corner) |
| `ix` | int | None | 菱形占地 x 格数 (用于自动计算尺寸和中心点) |
| `iy` | int | None | 菱形占地 y 格数 (用于自动计算尺寸和中心点) |
| `anialign` | int | 0 | 对齐模式: 0=edge(建筑/树), 1=center(角色) |

## Example

```bash
# Generate a sunset image
python comfyui.py "A beautiful sunset over a calm ocean, golden hour lighting"

# Generate a cyberpunk image with flux model
python comfyui.py "Cyberpunk city at night, neon lights, flying cars" --workflow flux_schnell_checkpoint.json

# Generate an image with custom filename
python comfyui.py "A cute cat sitting on a windowsill" --output cat_photo.png

# Generate a JPG image
python comfyui.py "Mountain landscape" --output mountain.jpg

# Generate an image to specific directory
python comfyui.py "Beach scene" --output /path/to/save

# Generate an image to specific directory with custom name
python comfyui.py "Beach scene" --output /path/to/save/beach_photo.png

# Generate a GBox animation file directly with custom dimensions and center point
# Specify .2dani.bmp extension to automatically convert the generated image to animation format with embedded binary
python comfyui.py "Pixel art character" --output character.2dani.bmp --width 160 --height 160 --center-x 80 --center-y 160

# Generate with isometric footprint auto-analysis (自动计算尺寸和中心点)
# ix/iy: 菱形占地格数, anialign: 0=edge(建筑/树), 1=center(角色)
python comfyui.py "ancient tree" --workflow z_image_blindbox.json --output tree.2dani.bmp --ix 3 --iy 3 --anialign 0
python comfyui.py "fairy character" --workflow z_image_blindbox.json --output fairy.2dani.bmp --ix 1 --iy 1 --anialign 1
```

## Notes

- Generation takes 20-60 seconds depending on workflow
- Images auto-open in system default viewer
- WebSocket timeout: 300 seconds

## 菱形占地自动分析 (Isometric Footprint Analysis)

当传入 `--ix` 和 `--iy` 参数时，系统会自动分析生成图片的菱形占地：

1. **检测底部顶点** — 双候选策略 (滑动窗口 + 低阈值)，V 形宽度匹配选择
2. **计算自然格子尺寸** — 比值法 + 高度突变法 + 扩展速率法，三者取最大
3. **找最佳中心格** — 距菱形几何中心最近的格子，平局时取更下更左的
4. **缩放到标准 128x64** — 自动计算 width, height, center_x, center_y
5. **输出占地格子数组** — 以中心格为 [0,0]，x 正方向右下，y 正方向右上

### 对齐模式 (anialign)

| 值 | 模式 | 适用 | 说明 |
|----|------|------|------|
| 0 | edge | 建筑、树 | 物体底部边缘贴合菱形下两条边 |
| 1 | center | 角色 | 物体脚部在菱形格中心位置 |

### 独立分析工具

```bash
# 分析图片并绘制菱形网格标注
python3 gboxani/lib/image_analyzer.py <图片> <NxM> [edge|center] [--std]

# 示例
python3 gboxani/lib/image_analyzer.py building.png 4x4 edge
python3 gboxani/lib/image_analyzer.py character.png 1x1 center
python3 gboxani/lib/image_analyzer.py tree.png 3x3 edge --std  # 同时输出标准化图片
```

## GBox Animation Tools

The `gboxani` sub-skill provides tools for converting GBox 2D animation formats.
You can generate `.2dani.bmp` files directly from `comfyui.py` by specifying the output filename with the `.2dani.bmp` extension (image data will be embedded as binary).

### Usage

Located in `gboxani/` directory.

```bash
# Convert .2dani.bmp to JSON
python3 gboxani/gbox_ani.py to_json <input.2dani.bmp> <output_dir>

# Convert JSON to .2dani.bmp
python3 gboxani/gbox_ani.py from_json <input.json> <output.2dani.bmp>

# Convert Image to .2dani.bmp
python3 gboxani/gbox_ani.py from_image <input.png> <output.2dani.bmp>
```

See [gboxani/SKILL.md](gboxani/SKILL.md) for detailed documentation.

