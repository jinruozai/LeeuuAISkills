---
name: "comfyui"
description: "Generate AI images using ComfyUI. Invoke when user wants to create images, generate pictures, or needs visual content from text descriptions."
argument-hint: "<prompt> [--workflow <name>] [--output <path>] [--width <n> --height <n>]"
---

# ComfyUI Image Generation Skill

Generates AI images via ComfyUI server.

## Prerequisites

- ComfyUI server running (default: `http://nat.leeuu.com:60080`)
- Python: `pip install websocket-client Pillow`

## Usage

```bash
# Basic
python comfyui.py "A beautiful sunset"

# With output file
python comfyui.py "A cute cat" --output cat.png

# With output directory
python comfyui.py "Mountain landscape" --output /path/to/save

# With output directory and filename
python comfyui.py "Beach scene" --output /path/to/save/beach.png

# With custom workflow (built-in)
python comfyui.py "Cyberpunk city" --workflow flux/schnell.json

# With external workflow
python comfyui.py "Portrait" --workflow /path/to/custom_workflow.json

# With resize
python comfyui.py "Pixel art" --output art.png --width 512 --height 512
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | required | Image description |
| `server` | str | `http://nat.leeuu.com:60080` | ComfyUI server address |
| `workflow` | str | `z_image.json` | Built-in workflow name (supports subdirs e.g. `flux/schnell.json`) or external absolute path |
| `output` | str | None | Output directory or file path. If omitted, returns image binary data |
| `width` | int | None | Target width for resizing |
| `height` | int | None | Target height for resizing |

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `z_image.json` | Z-Image Turbo, fast (~30s) |

## Notes

- If `output` is provided, images are saved and paths are returned
- If `output` is omitted, raw image bytes are returned for the caller to handle
- Workflow: tries as file path first, then looks in built-in `workflows/` directory
- Generation takes 20-60 seconds depending on workflow
- WebSocket timeout: 300 seconds
