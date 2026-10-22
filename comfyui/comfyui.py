#!/usr/bin/env python3
"""ComfyUI Image Generation Client"""

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
from PIL import Image

DEFAULT_SERVER = "nat.leeuu.com:60080"
DEFAULT_WORKFLOW = "z_image.json"
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp')

def _get_logger():
    logger = logging.getLogger('skill.comfyui')
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

_logger = _get_logger()


def _parse_output_path(output):
    """Parse output into (dir, filename). Returns (None, None) if output is None."""
    if not output:
        return None, None
    if any(output.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
        return os.path.dirname(output) or '.', os.path.basename(output)
    return output, None


def _resolve_workflow(workflow_path):
    """Resolve workflow: try as file path first, then look in built-in workflows/ dir."""
    skill_dir = os.path.dirname(os.path.abspath(__file__))

    if workflow_path:
        # Try as-is (absolute or relative path)
        if os.path.isfile(workflow_path):
            return workflow_path
        # Try in built-in workflows directory
        builtin = os.path.join(skill_dir, "workflows", workflow_path)
        if os.path.isfile(builtin):
            return builtin
        # Try appending .json
        if not workflow_path.endswith('.json'):
            builtin_json = builtin + '.json'
            if os.path.isfile(builtin_json):
                return builtin_json

    # Fallback to default
    return os.path.join(skill_dir, "workflows", DEFAULT_WORKFLOW)


def _inject_prompt(workflow_data, prompt_text):
    """Inject prompt text into the first CLIPTextEncode node (prefer node '6')."""
    if not prompt_text:
        return
    prompt_node = None
    for node_id, node in workflow_data.items():
        if node.get("class_type") == "CLIPTextEncode" and "text" in node.get("inputs", {}):
            if not prompt_node or node_id == "6":
                prompt_node = node_id
    if prompt_node:
        workflow_data[prompt_node]["inputs"]["text"] = prompt_text
        _logger.info(f"Prompt injected into node {prompt_node}")


def _add_websocket_node(workflow_data):
    """Add SaveImageWebsocket node if not already present."""
    for node in workflow_data.values():
        if node.get("class_type") == "SaveImageWebsocket":
            return

    # Find image output source
    input_source = None
    for node_id, node in workflow_data.items():
        if node.get("class_type") == "SaveImage" and "images" in node.get("inputs", {}):
            input_source = node["inputs"]["images"]
            break
    if not input_source:
        for node_id, node in workflow_data.items():
            if node.get("class_type") == "VAEDecode":
                input_source = [node_id, 0]
                break
    if not input_source:
        return

    workflow_data["save_image_websocket_node"] = {
        "class_type": "SaveImageWebsocket",
        "inputs": {"images": input_source}
    }


class ComfyUI:
    def __init__(self, server_addr=None):
        addr = server_addr or DEFAULT_SERVER
        # Strip protocol prefix to get host:port
        match = re.match(r'^(?:https?|wss?)://(.+?)/?$', addr)
        self.server_address = match.group(1) if match else addr
        self.client_id = str(uuid.uuid4())

    def _queue_prompt(self, prompt):
        data = json.dumps({"prompt": prompt, "client_id": self.client_id}).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def _receive_images(self, ws, workflow):
        """Submit workflow and receive images via WebSocket."""
        _logger.info("Submitting workflow...")
        prompt_id = self._queue_prompt(workflow)['prompt_id']
        _logger.info(f"Waiting for images, prompt_id: {prompt_id}")

        output_images = {}
        current_node = ""
        img_received = False
        last_msg_time = time.time()

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
                                _logger.info("Workflow complete!")
                                break
                            current_node = data['node']
                else:
                    # Binary image data (skip 8-byte header)
                    images_output = output_images.setdefault(current_node, [])
                    images_output.append(out[8:])
                    img_received = True

                if img_received and (time.time() - last_msg_time) > 15:
                    break

            except websocket.WebSocketTimeoutException:
                if img_received:
                    break
                raise

        return output_images

    def generate(self, prompt_text=None, workflow_path=None, output=None,
                 width=None, height=None):
        """
        Generate images from ComfyUI.

        Returns:
            If output is provided: list of saved file paths
            If output is None: list of raw image bytes (PNG format)
        """
        # Resolve workflow
        wf_file = _resolve_workflow(workflow_path)
        _logger.info(f"Workflow: {wf_file}")

        with open(wf_file, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)

        _inject_prompt(workflow_data, prompt_text)
        _add_websocket_node(workflow_data)

        # Connect and generate
        ws = websocket.WebSocket()
        ws.settimeout(300)
        try:
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
            images = self._receive_images(ws, workflow_data)
        finally:
            try:
                ws.close()
            except Exception:
                pass

        # Process results
        output_dir, output_filename = _parse_output_path(output)
        results = []
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        count = 0

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        for node_id, image_list in images.items():
            for image_data in image_list:
                image = Image.open(io.BytesIO(image_data))

                # Resize if both dimensions provided
                if width and height:
                    image = image.resize((width, height), Image.Resampling.LANCZOS)

                if output_dir:
                    # Save to file
                    if output_filename and count == 0:
                        name = output_filename
                    else:
                        name = f"comfyui_{timestamp}_{unique_id}_{count}.png"
                    path = os.path.join(output_dir, name)
                    image.save(path)
                    _logger.info(f"Saved: {path}")
                    results.append(path)
                else:
                    # Return as PNG bytes
                    buf = io.BytesIO()
                    image.save(buf, format='PNG')
                    results.append(buf.getvalue())
                    _logger.info(f"Image {count}: {len(results[-1])} bytes")

                count += 1

        _logger.info(f"Generated {count} image(s)")
        return results


def generate_image(prompt, server=None, workflow=None, output=None,
                   width=None, height=None):
    """Convenience function for generating images."""
    comfy = ComfyUI(server)
    return comfy.generate(prompt, workflow, output, width, height)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate AI images using ComfyUI')
    parser.add_argument('prompt', help='Image description')
    parser.add_argument('--server', default=None, help='ComfyUI server address')
    parser.add_argument('--workflow', default=None, help='Workflow name or path')
    parser.add_argument('--output', help='Output directory or file path')
    parser.add_argument('--width', type=int, help='Target width')
    parser.add_argument('--height', type=int, help='Target height')

    args = parser.parse_args()
    results = generate_image(
        prompt=args.prompt, server=args.server, workflow=args.workflow,
        output=args.output, width=args.width, height=args.height
    )
    if args.output:
        print(f'Saved: {results}')
    else:
        print(f'Generated {len(results)} image(s) as binary data')
