---
name: "gbox_2dani"
description: "GBox 2D Animation Format Converter. Convert between .2dani.bmp, JSON, and images. Supports scaling and fitting animations."
argument-hint: "<command> <input> [options]"
---

# GBox 2D Animation Converter

Convert between GBox `.2dani.bmp` binary format, JSON, and images.

## Prerequisites

- Python: `pip install Pillow`

## Python API

All interfaces support flexible input/output:
- **Input**: `str` (file path) or `bytes`/`dict` (data in memory)
- **Output**: pass `output` path → writes file, returns path; omit → returns `bytes`/`dict`

```python
from gbox_2dani import image_to_2dani, json_to_2dani, parse_2dani, scale_2dani, fit_2dani

# 1. Image → 2dani
data = image_to_2dani("char.png", width=200, height=200)                    # returns bytes
image_to_2dani("char.png", 200, 200, center_x=100, center_y=180, output="char.2dani.bmp")
image_to_2dani(png_bytes, 200, 200, output="char.2dani.bmp")                # bytes input

# 2. JSON → 2dani
data = json_to_2dani(json_dict, preview_image="preview.png", embed=True)
json_to_2dani("anim.json", output="anim.2dani.bmp")

# 3. 2dani → JSON
result = parse_2dani("char.2dani.bmp")                                       # images as base64
result = parse_2dani("char.2dani.bmp", output_dir="./extracted")             # images to files
result = parse_2dani(ani_bytes)                                              # bytes input

# 4. Scale 2dani
data = scale_2dani("char.2dani.bmp", scale_factor=2.0)                      # returns bytes
scale_2dani("char.2dani.bmp", 0.5, output="char_small.2dani.bmp")

# 5. Fit 2dani to target size (with optional re-center)
data = fit_2dani("char.2dani.bmp", width=256, height=256)
fit_2dani("char.2dani.bmp", 256, 256, center_x=128, center_y=240, output="fitted.2dani.bmp")
```

## CLI Usage

```bash
# Image → 2dani
python gbox_2dani.py from_image char.png char.2dani.bmp --width 200 --height 200
python gbox_2dani.py from_image char.png char.2dani.bmp --width 200 --height 200 --center-x 100 --center-y 180

# JSON → 2dani
python gbox_2dani.py from_json anim.json anim.2dani.bmp --embed

# 2dani → JSON (extracts images to output dir)
python gbox_2dani.py to_json char.2dani.bmp ./output --base-name char

# Scale by factor
python gbox_2dani.py scale char.2dani.bmp --scale 2.0 --output char_big.2dani.bmp

# Fit to target size with optional center point
python gbox_2dani.py fit char.2dani.bmp --width 256 --height 256
python gbox_2dani.py fit char.2dani.bmp --width 256 --height 256 --center-x 128 --center-y 240
```

## Parameters

### image_to_2dani
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| image | str/bytes | required | Image file path or binary data |
| width | int | required | Animation width |
| height | int | required | Animation height |
| center_x | float | width/2 | Center point X |
| center_y | float | height/2 | Center point Y |
| embed | bool | True | Embed image binary in 2dani |
| output | str | None | Output path (None = return bytes) |

### json_to_2dani
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| data | str/dict | required | JSON file path or dict |
| preview_image | str/bytes | None | Preview image |
| embed | bool | False | Embed linked images as binary |
| output | str | None | Output path |

### parse_2dani
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| data | str/bytes | required | 2dani file path or binary data |
| output_dir | str | None | Extract images here; None = base64 in JSON |

### scale_2dani
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| data | str/bytes | required | 2dani file path or binary data |
| scale_factor | float | required | Scale factor |
| output | str | None | Output path |

### fit_2dani
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| data | str/bytes | required | 2dani file path or binary data |
| width | int | required | Target width |
| height | int | required | Target height |
| center_x | float | None | New center X (None = keep original) |
| center_y | float | None | New center Y (None = keep original) |
| output | str | None | Output path |

## Supported Image Formats

- Standard: PNG, JPEG, GIF
- GBox: JGEIMGFLAG (JPEG+GIF mask), IMG1 (raw pixel), ALE

## 菱形占地自动分析 (Isometric Footprint Analysis)

`lib/image_analyzer.py` 分析等距图片的菱形占地，自动算出标准尺寸和中心点，结果可直接传给 `image_to_2dani`。
依赖：`pip install Pillow numpy`

1. **检测底部顶点** — 双候选策略 (滑动窗口 + 低阈值)，V 形宽度匹配选择
2. **计算自然格子尺寸** — 比值法 + 高度突变法 + 扩展速率法，三者取最大
3. **找最佳中心格** — 距菱形几何中心最近的格子，平局时取更下更左的
4. **缩放到标准 128x64** — 自动计算 width, height, center_x, center_y
5. **输出占地格子数组** — 以中心格为 [0,0]，x 正方向右下，y 正方向右上

### 对齐模式

| 值 | 模式 | 适用 | 说明 |
|----|------|------|------|
| edge | 0 | 建筑、树 | 物体底部边缘贴合菱形下两条边 |
| center | 1 | 角色 | 物体脚部在菱形格中心位置 |

```bash
# 分析图片并绘制菱形网格标注
python3 lib/image_analyzer.py <图片> <NxM> [edge|center] [--std]

python3 lib/image_analyzer.py building.png 4x4 edge
python3 lib/image_analyzer.py character.png 1x1 center
python3 lib/image_analyzer.py tree.png 3x3 edge --std  # 同时输出标准化图片
```

典型流程：`comfyui` 出图 → `image_analyzer` 算出尺寸和中心点 → `image_to_2dani` 生成 `.2dani.bmp`。
