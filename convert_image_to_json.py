#!/usr/bin/env python3
"""
Convert image to JSON format with embedded image data
"""

import os
import sys
import json

# Add gbox_2dani lib to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gbox_2dani'))

from gbox_2dani import parse_2dani

# Input image path
input_image = "/Users/gooooo/Documents/ai_skills/test/output/test_1.png"

# Output JSON path
output_json = "/Users/gooooo/Documents/ai_skills/test/output/test_1.json"

# First convert image to 2dani
from gbox_2dani import image_to_2dani

print("Converting image to 2dani...")
temp_2dani = "/Users/gooooo/Documents/ai_skills/test/output/test_1_temp.2dani.bmp"
image_to_2dani(input_image, 512, 512, embed=True, output=temp_2dani)

print("Converting 2dani to JSON with embedded images...")
# Parse 2dani to JSON with embedded images (output_dir=None)
json_data = parse_2dani(temp_2dani, output_dir=None)

# Save JSON to file
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

# Clean up temporary 2dani file
os.remove(temp_2dani)

print(f"Successfully converted image to JSON: {output_json}")
