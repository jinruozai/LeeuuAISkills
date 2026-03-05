---
name: "gboxani"
description: "GBox 2D Animation Format Converter. Convert between .2dani.bmp, JSON, and Images."
---

# GBox 2D Animation Format Converter

This tool provides capabilities to convert GBox 2D animation files (default extension `.2dani.bmp`) to/from JSON and Images. It is located in the `gboxani` subdirectory of the ComfyUI skill.

## Usage

Run the python script directly from the `gboxani` directory:

```bash
python3 gbox_ani.py <command> [arguments]
```

## Commands

### 1. `to_json`
Convert `.2dani.bmp` file to JSON format (and extract images).

```bash
python3 gbox_ani.py to_json <input_file> <output_dir> [--base-name BASE_NAME]
```
- `input_file`: Path to source `.2dani.bmp` file
- `output_dir`: Directory to save JSON and extracted images
- `--base-name`: (Optional) Base name for output files

### 2. `from_json`
Convert JSON file back to `.2dani.bmp` format.

```bash
python3 gbox_ani.py from_json <input_file> <output_file>
```
- `input_file`: Path to source JSON file
- `output_file`: Path to save `.2dani.bmp` file

### 3. `from_image`
Create a simple `.2dani.bmp` animation from a single image.

```bash
python3 gbox_ani.py from_image <input_file> <output_file> [--width W] [--height H]
```
- `input_file`: Path to source image
- `output_file`: Path to save `.2dani.bmp` file
- `--width`, `--height`: Dimensions of the animation (default: 200x200)
- `--center-x`, `--center-y`: Center point coordinates (optional)
