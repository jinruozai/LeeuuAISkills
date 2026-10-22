#!/usr/bin/env python3
"""GBData Editor — FastAPI backend server."""

import os
import sys
import json
import time
import random
import asyncio
import argparse
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from watchfiles import awatch

# ── ID generation ──

def gen_id() -> int:
    ts = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand = random.randint(0, 0xFFFF)
    return (ts << 16) | rand

# ── Globals ──

DATA_ROOT: Path = Path("./data")
GBDATA_PATH: Path = Path("./data.gbdata")
STATIC_DIR = Path(__file__).parent / "static"

# Suppress echo for our own writes
_recent_writes: dict[str, float] = {}
WRITE_SUPPRESS_TTL = 1.0  # seconds


def _mark_written(path: str):
    _recent_writes[path] = time.time()


def _is_self_write(path: str) -> bool:
    ts = _recent_writes.get(path)
    if ts and (time.time() - ts) < WRITE_SUPPRESS_TTL:
        del _recent_writes[path]
        return True
    return False


# ── Project data ──

def load_gbdata() -> dict:
    if GBDATA_PATH.exists():
        with open(GBDATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "name": "New Project", "types": {}, "fields": {}, "categories": {}}


def save_gbdata(data: dict):
    with open(GBDATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    _mark_written(str(GBDATA_PATH.resolve()))


def _sanitize_filename(name: str) -> str:
    if not name:
        return ""
    forbidden = '/\\:*?"<>|'
    result = "".join("_" if c in forbidden else c for c in name)
    result = result.replace(" ", "_")
    return result


def _entity_filename(entity: dict, gbdata: dict, category_key: str) -> str:
    _id = entity.get("_id", 0)
    # Find title field for this category
    cat = gbdata.get("categories", {}).get(category_key, {})
    fields_def = gbdata.get("fields", {})
    name = ""
    for f in cat.get("fields", []):
        fkey = f if isinstance(f, str) else f.get("key", "")
        fdef = fields_def.get(fkey, {})
        if fdef.get("card_slot") == "title":
            name = str(entity.get(fkey, ""))
            break
    if not name:
        # Fallback: first string-ish field
        for f in cat.get("fields", []):
            fkey = f if isinstance(f, str) else f.get("key", "")
            val = entity.get(fkey)
            if isinstance(val, str) and val:
                name = val
                break
    sanitized = _sanitize_filename(name)
    if sanitized:
        return f"{_id}_{sanitized}.json"
    return f"{_id}.json"


def _category_dir(category_key: str) -> Path:
    return DATA_ROOT / category_key


def _list_entities(category_key: str) -> list[dict]:
    cat_dir = _category_dir(category_key)
    if not cat_dir.exists():
        return []
    entities = []
    for f in sorted(cat_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            data["_file"] = f.name
            entities.append(data)
        except Exception:
            pass
    return entities


def _find_entity_file(category_key: str, entity_id: int) -> Path | None:
    cat_dir = _category_dir(category_key)
    if not cat_dir.exists():
        return None
    id_prefix = str(entity_id)
    for f in cat_dir.glob("*.json"):
        if f.name.startswith(id_prefix):
            return f
        # Also check inside
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if data.get("_id") == entity_id:
                return f
        except Exception:
            pass
    return None


# ── WebSocket manager ──

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message, ensure_ascii=False)
        for ws in self.connections[:]:
            try:
                await ws.send_text(data)
            except Exception:
                self.connections.remove(ws)

manager = ConnectionManager()


# ── File watcher ──

async def watch_files():
    watch_path = DATA_ROOT if DATA_ROOT.exists() else Path(".")
    async for changes in awatch(watch_path, GBDATA_PATH.parent):
        for change_type, path_str in changes:
            if _is_self_write(str(Path(path_str).resolve())):
                continue
            path = Path(path_str)
            # .gbdata changed
            if path.resolve() == GBDATA_PATH.resolve():
                try:
                    data = load_gbdata()
                    await manager.broadcast({"type": "project_changed", "data": data})
                except Exception:
                    pass
                continue
            # Entity JSON changed
            if path.suffix == ".json" and not path.name.startswith("_"):
                try:
                    rel = path.relative_to(DATA_ROOT)
                    parts = rel.parts
                    if len(parts) == 2:
                        category = parts[0]
                        if path.exists():
                            with open(path, "r", encoding="utf-8") as f:
                                entity_data = json.load(f)
                            entity_data["_file"] = path.name
                            await manager.broadcast({
                                "type": "entity_changed",
                                "category": category,
                                "id": entity_data.get("_id"),
                                "data": entity_data
                            })
                        else:
                            # File deleted
                            await manager.broadcast({
                                "type": "entity_deleted",
                                "category": category,
                                "filename": path.name
                            })
                except Exception:
                    pass


# ── App lifecycle ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(watch_files())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


# ── API routes ──

@app.get("/api/project")
async def get_project():
    return load_gbdata()


@app.put("/api/project")
async def update_project(data: dict):
    save_gbdata(data)
    return {"ok": True}


@app.get("/api/categories/{key}/entities")
async def list_entities(key: str):
    return _list_entities(key)


@app.get("/api/categories/{key}/entities/{entity_id}")
async def get_entity(key: str, entity_id: int):
    f = _find_entity_file(key, entity_id)
    if not f:
        raise HTTPException(404, "Entity not found")
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    data["_file"] = f.name
    return data


@app.put("/api/categories/{key}/entities/{entity_id}")
async def save_entity(key: str, entity_id: int, body: dict):
    entity = body.get("data", body)
    entity["_id"] = entity_id
    gbdata = load_gbdata()

    # Determine filename
    new_filename = _entity_filename(entity, gbdata, key)
    cat_dir = _category_dir(key)
    cat_dir.mkdir(parents=True, exist_ok=True)

    # Find old file and remove if name changed
    old_file = _find_entity_file(key, entity_id)
    new_path = cat_dir / new_filename

    if old_file and old_file.resolve() != new_path.resolve():
        old_file.unlink()
        _mark_written(str(old_file.resolve()))

    # Remove internal _file field before saving
    save_data = {k: v for k, v in entity.items() if k != "_file"}
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=4)
    _mark_written(str(new_path.resolve()))

    save_data["_file"] = new_filename
    return save_data


@app.post("/api/categories/{key}/entities")
async def create_entity(key: str, body: dict):
    entity = body.get("data", body)
    if "_id" not in entity:
        entity["_id"] = gen_id()
    gbdata = load_gbdata()
    filename = _entity_filename(entity, gbdata, key)
    cat_dir = _category_dir(key)
    cat_dir.mkdir(parents=True, exist_ok=True)
    filepath = cat_dir / filename
    if filepath.exists():
        raise HTTPException(409, "Entity file already exists")
    save_data = {k: v for k, v in entity.items() if k != "_file"}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=4)
    _mark_written(str(filepath.resolve()))
    save_data["_file"] = filename
    return save_data


@app.delete("/api/categories/{key}/entities/{entity_id}")
async def delete_entity(key: str, entity_id: int):
    f = _find_entity_file(key, entity_id)
    if not f:
        raise HTTPException(404, "Entity not found")
    f.unlink()
    _mark_written(str(f.resolve()))
    return {"ok": True}


@app.get("/api/gen_id")
async def api_gen_id():
    return {"id": gen_id()}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── Static files ──

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── CLI ──

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GBData Editor Server")
    parser.add_argument("gbdata", nargs="?", default=None, help="Path to .gbdata file")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.gbdata:
        GBDATA_PATH = Path(args.gbdata).resolve()
        DATA_ROOT = GBDATA_PATH.parent
    else:
        # Look for .gbdata in current directory
        found = list(Path(".").glob("*.gbdata"))
        if found:
            GBDATA_PATH = found[0].resolve()
            DATA_ROOT = GBDATA_PATH.parent
        else:
            print("No .gbdata file specified or found. Creating default.")
            GBDATA_PATH = Path("./project.gbdata").resolve()
            DATA_ROOT = Path(".").resolve()
            if not GBDATA_PATH.exists():
                save_gbdata(load_gbdata())

    print(f"Project: {GBDATA_PATH}")
    print(f"Data root: {DATA_ROOT}")
    print(f"Editor: http://{args.host}:{args.port}")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
