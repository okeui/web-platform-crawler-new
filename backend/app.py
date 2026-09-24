import os
import asyncio
import threading
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from storage import StorageManager
from crawler_engine import CrawlerEngine

app = FastAPI(title="Web Platform FAQ Checker API", version="1.0.0")

# Enable CORS for local desktop UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = StorageManager()

# Global Log Queue for WebSockets
active_websockets: List[WebSocket] = []
ws_loop: Optional[asyncio.AbstractEventLoop] = None

def broadcast_log(message: str, level: str = "INFO"):
    """Callback triggered by CrawlerEngine to broadcast log via WebSockets."""
    status = crawler.get_status()
    payload = {
        "type": "log",
        "message": message,
        "level": level,
        "status": status
    }
    
    # Broadcast to active WebSockets safely
    for ws in list(active_websockets):
        try:
            if ws_loop and ws_loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_json(payload), ws_loop)
        except Exception as e:
            print(f"Error broadcasting to WebSocket: {e}")

crawler = CrawlerEngine(log_callback=broadcast_log)

# Pydantic Request Models
class NodeModel(BaseModel):
    id: Optional[str] = None
    path: str
    keywords: List[str]
    enabled: Optional[bool] = True

class PinModel(BaseModel):
    pin: str

class SettingsModel(BaseModel):
    target_url: Optional[str] = "https://login.gov.taipei/login.php"
    search_system_name: Optional[str] = "網站整合平臺"
    headless: Optional[bool] = False
    implicit_wait: Optional[int] = 10
    click_timeout: Optional[int] = 20
    log_dir: Optional[str] = ".\\"

# API Routes
@app.on_event("startup")
async def startup_event():
    global ws_loop
    ws_loop = asyncio.get_running_loop()

@app.get("/api/nodes")
def get_nodes():
    return {"nodes": storage.get_nodes()}

@app.post("/api/nodes")
def add_node(node: NodeModel):
    if not node.path.strip():
        raise HTTPException(status_code=400, detail="Path cannot be empty")
    new_node = storage.add_node(node.path, node.keywords, node.enabled)
    return {"status": "success", "node": new_node}

@app.put("/api/nodes/{node_id}")
def update_node(node_id: str, node: NodeModel):
    updated = storage.update_node(node_id, node.path, node.keywords, node.enabled)
    if not updated:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "success", "node": updated}

@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    success = storage.delete_node(node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "success"}

@app.post("/api/nodes/save")
def save_all_nodes(data: Dict[str, Any]):
    """Batch save all nodes from frontend."""
    nodes = data.get("nodes", [])
    current_data = storage.load()
    current_data["nodes"] = nodes
    success = storage.save(current_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save nodes configuration")
    return {"status": "success", "nodes": storage.get_nodes()}

@app.get("/api/settings")
def get_settings():
    return storage.get_settings()

@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    updated = storage.update_settings(settings.dict(exclude_unset=True))
    return {"status": "success", "settings": updated}

@app.get("/api/crawler/status")
def get_crawler_status():
    return crawler.get_status()

@app.post("/api/crawler/start")
def start_crawler():
    if crawler.is_running():
        raise HTTPException(status_code=400, detail="Crawler is already running")

    paths_dict = storage.get_paths_and_checklists_dict()
    if not paths_dict:
        raise HTTPException(status_code=400, detail="No active path nodes configured to check!")

    settings = storage.get_settings()

    # Launch crawler in background thread
    crawler_thread = threading.Thread(
        target=crawler.run,
        args=(paths_dict, settings),
        daemon=True
    )
    crawler_thread.start()
    return {"status": "started"}

@app.post("/api/crawler/stop")
def stop_crawler():
    if not crawler.is_running():
        return {"status": "not_running"}
    crawler.request_stop()
    return {"status": "stop_requested"}

@app.post("/api/crawler/pin")
def send_pin(pin_data: PinModel):
    if not crawler.is_running():
        raise HTTPException(status_code=400, detail="Crawler is not running")
    crawler.set_pin_code(pin_data.pin)
    return {"status": "pin_sent"}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    # Send initial status
    await websocket.send_json({
        "type": "status_init",
        "status": crawler.get_status()
    })
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

# Serve Frontend SPA
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
