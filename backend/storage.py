import json
import os
import sys
import uuid
import shutil
from typing import Dict, List, Any, Optional

def get_app_dir() -> str:
    """Returns the root directory of the application.
    If packaged with PyInstaller, returns directory containing executable.
    Otherwise returns workspace project root.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_config_dir() -> str:
    """Returns the path to the dedicated config directory."""
    config_dir = os.path.join(get_app_dir(), "config")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def get_logs_dir() -> str:
    """Returns the path to the dedicated logs directory."""
    logs_dir = os.path.join(get_app_dir(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def get_default_config_path() -> str:
    """Returns path to nodes_config.json inside config folder, automatically migrating legacy config if present."""
    config_dir = get_config_dir()
    target_config_path = os.path.join(config_dir, "nodes_config.json")
    
    if not os.path.exists(target_config_path):
        legacy_config_path = os.path.join(get_app_dir(), "nodes_config.json")
        if os.path.exists(legacy_config_path):
            try:
                shutil.copy2(legacy_config_path, target_config_path)
            except Exception as e:
                print(f"Error copying legacy config file: {e}")
                
    return target_config_path

DEFAULT_CONFIG_PATH = get_default_config_path()

DEFAULT_NODES = [
    {
        "id": "node_1",
        "path": "業務專區>地政問答>地籍謄本及圖資申請",
        "keywords": [
            "地政電子謄本和地政事務所核發的謄本有什麼不同？",
            "如何透過網路申請地籍謄本和查詢閱覽地政資料？其收費方式及收費標準為何？",
            "如何申請取得地政電子資料？其檔案格式為何？可不可以申請其他縣市的地政電子資料？",
            "使用北北桃地政資訊網路e點通服務時，查詢到地籍圖或建物測量成果圖，用戶端電腦卻無法顯示或列印時，如何處理？"
        ],
        "enabled": True
    },
    {
        "id": "node_2",
        "path": "業務專區>地政問答>不動產資訊查詢",
        "keywords": [
            "原本的臺北地政雲不見了？",
            "新一代地政雲公地查詢如何使用門牌定位？為何查詢結果清單沒有列私有地?",
            "新一代地政雲查詢後畫面東西越來越多要怎麼清除？"
        ],
        "enabled": True
    },
    {
        "id": "node_3",
        "path": "業務專區>地政問答>地價類",
        "keywords": [
            "土地增值稅試算功能在哪？是否需要會員登入？"
        ],
        "enabled": True
    }
]

DEFAULT_SETTINGS = {
    "target_url": "https://login.gov.taipei/login.php",
    "search_system_name": "網站整合平臺",
    "headless": False,
    "implicit_wait": 10,
    "click_timeout": 20,
    "log_dir": get_logs_dir()
}

class StorageManager:
    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            filepath = get_default_config_path()
        self.filepath = os.path.abspath(filepath)
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            initial_data = {
                "nodes": DEFAULT_NODES,
                "settings": DEFAULT_SETTINGS
            }
            self.save(initial_data)
            return initial_data

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "nodes" not in data:
                    data["nodes"] = DEFAULT_NODES
                if "settings" not in data:
                    data["settings"] = DEFAULT_SETTINGS
                return data
        except Exception as e:
            print(f"Error loading config file {self.filepath}: {e}")
            return {"nodes": DEFAULT_NODES, "settings": DEFAULT_SETTINGS}

    def save(self, data: Optional[Dict[str, Any]] = None) -> bool:
        if data is not None:
            self.data = data
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config file {self.filepath}: {e}")
            return False

    def get_nodes(self) -> List[Dict[str, Any]]:
        return self.data.get("nodes", [])

    def add_node(self, path: str, keywords: List[str], enabled: bool = True) -> Dict[str, Any]:
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        new_node = {
            "id": node_id,
            "path": path,
            "keywords": keywords,
            "enabled": enabled
        }
        self.data["nodes"].append(new_node)
        self.save()
        return new_node

    def update_node(self, node_id: str, path: Optional[str] = None, keywords: Optional[List[str]] = None, enabled: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        for node in self.data["nodes"]:
            if node["id"] == node_id:
                if path is not None:
                    node["path"] = path
                if keywords is not None:
                    node["keywords"] = keywords
                if enabled is not None:
                    node["enabled"] = enabled
                self.save()
                return node
        return None

    def delete_node(self, node_id: str) -> bool:
        initial_len = len(self.data["nodes"])
        self.data["nodes"] = [n for n in self.data["nodes"] if n["id"] != node_id]
        if len(self.data["nodes"]) < initial_len:
            self.save()
            return True
        return False

    def get_settings(self) -> Dict[str, Any]:
        settings = self.data.get("settings", {})
        merged = DEFAULT_SETTINGS.copy()
        merged.update(settings)
        if not merged.get("log_dir") or merged.get("log_dir") in [".\\", ".", "./"]:
            merged["log_dir"] = get_logs_dir()
        return merged

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        settings = self.get_settings()
        settings.update(new_settings)
        self.data["settings"] = settings
        self.save()
        return settings

    def get_paths_and_checklists_dict(self) -> Dict[str, List[str]]:
        """Converts active nodes to the dict format expected by the crawler engine."""
        result = {}
        for node in self.data.get("nodes", []):
            if node.get("enabled", True):
                path = node.get("path", "").strip()
                keywords = node.get("keywords", [])
                if path and keywords:
                    result[path] = keywords
        return result
