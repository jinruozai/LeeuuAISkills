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

# Generate a GBox animation file directly
# Specify .2dani.bmp extension to automatically convert the generated image to animation format with embedded binary
python comfyui.py "Pixel art character" --output character.2dani.bmp
```

## Notes

- Generation takes 20-60 seconds depending on workflow
- Images auto-open in system default viewer
- WebSocket timeout: 300 seconds

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

