"""Drive device abstraction for APA-OS."""
import os
import time
import uuid
from typing import Dict, Any, Optional, List

from ..device import Device, DeviceInfo, DeviceStatus


class DriveDevice(Device):
    """Abstract representation of cloud drive."""

    def __init__(self, device_id: str, provider: str = "google_drive", **kwargs):
        super().__init__(device_id)
        if provider not in ("google_drive", "onedrive"):
            raise ValueError(f"Unsupported provider: {provider}")
        self.provider = provider
        self._connected = False
        self._virtual_fs: Dict[str, dict] = {}
        self._init_virtual_fs()

    def _init_virtual_fs(self):
        self._virtual_fs["root"] = {
            "id": "root",
            "name": "root",
            "mime_type": "application/vnd.google-apps.folder",
            "size": 0,
            "created_time": time.time(),
            "modified_time": time.time(),
            "description": "Root folder",
            "file_extension": "",
            "parent": None,
        }

    def _path_to_id(self, folder_path: str) -> str:
        folder_path = folder_path.replace("\\", "/").rstrip("/") or "/"
        if folder_path == "/":
            return "root"
        for entry in self._virtual_fs.values():
            if entry.get("parent") == "root" and entry.get("name") == folder_path.lstrip("/"):
                return entry["id"]
        return "root"

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _now(self) -> float:
        return time.time()

    async def connect(self) -> Dict[str, Any]:
        self._connected = True
        return {"status": "connected", "provider": self.provider, "message": f"Connected to {self.provider}"}

    async def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        return {"status": "disconnected", "provider": self.provider, "message": f"Disconnected from {self.provider}"}

    async def status(self) -> Dict[str, Any]:
        return {"connected": self._connected, "provider": self.provider, "device_id": self.device_id}

    async def capabilities(self) -> List[str]:
        return ["drive", "file_storage", "file_sync"]

    async def get_info(self) -> DeviceInfo:
        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED if self._connected else DeviceStatus.DISCONNECTED,
            is_locked=False,
            battery_level=None,
            foreground_app=None,
            installed_apps={"drive"},
            capabilities={"drive"},
            device_type="drive",
            model_name=f"{self.provider.replace('_', ' ').title()}",
            os_version="cloud",
            additional={
                "provider": self.provider,
                "storage_type": "cloud",
                "connected": self._connected,
                "file_count": len(self._virtual_fs) - 1,
            },
        )

    async def list_files(self, folder_path: str = "/") -> List[Dict[str, Any]]:
        parent_id = self._path_to_id(folder_path)
        result = []
        for entry in self._virtual_fs.values():
            if entry.get("parent") == parent_id and entry["id"] != "root":
                result.append({
                    "id": entry["id"],
                    "name": entry["name"],
                    "mime_type": entry["mime_type"],
                    "size": entry["size"],
                    "modified_time": entry["modified_time"],
                    "file_extension": entry.get("file_extension", ""),
                })
        return result

    async def search_files(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        result = []
        for entry in self._virtual_fs.values():
            if entry["id"] == "root":
                continue
            if query_lower in entry["name"].lower() or query_lower in entry.get("description", "").lower():
                result.append({
                    "id": entry["id"],
                    "name": entry["name"],
                    "mime_type": entry["mime_type"],
                    "size": entry["size"],
                    "modified_time": entry["modified_time"],
                    "file_extension": entry.get("file_extension", ""),
                })
        return result

    async def download_file(self, file_id: str, destination_path: str) -> Dict[str, Any]:
        entry = self._virtual_fs.get(file_id)
        if entry is None:
            return {"status": "error", "message": f"File {file_id} not found"}
        os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
        with open(destination_path, "w") as f:
            f.write(f"Mock content for {entry['name']}")
        return {"status": "downloaded", "file_path": destination_path, "size": entry["size"]}

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        entry = self._virtual_fs.get(file_id)
        if entry is None:
            return {"status": "error", "message": f"File {file_id} not found"}
        return {
            "id": entry["id"],
            "name": entry["name"],
            "mime_type": entry["mime_type"],
            "size": entry["size"],
            "created_time": entry["created_time"],
            "modified_time": entry["modified_time"],
            "description": entry.get("description", ""),
        }

    async def upload_file(self, file_path: str, folder_path: str = "/") -> Dict[str, Any]:
        name = os.path.basename(file_path)
        parent_id = self._path_to_id(folder_path)
        ext = os.path.splitext(name)[1] or ""
        mime = "text/plain" if ext in (".txt", ".md", ".csv") else "application/octet-stream"
        if ext in (".jpg", ".png", ".gif"):
            mime = f"image/{ext[1:]}"
        file_id = self._generate_id()
        now = self._now()
        self._virtual_fs[file_id] = {
            "id": file_id,
            "name": name,
            "mime_type": mime,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "created_time": now,
            "modified_time": now,
            "description": "",
            "file_extension": ext,
            "parent": parent_id,
        }
        return {"file_id": file_id, "name": name, "status": "uploaded"}

    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        if file_id == "root":
            return {"status": "error", "message": "Cannot delete root folder"}
        if file_id not in self._virtual_fs:
            return {"status": "error", "message": f"File {file_id} not found"}
        children = [eid for eid, e in self._virtual_fs.items() if e.get("parent") == file_id]
        for cid in children:
            del self._virtual_fs[cid]
        del self._virtual_fs[file_id]
        return {"status": "deleted", "file_id": file_id}

    async def create_folder(self, name: str, parent_path: str = "/") -> Dict[str, Any]:
        parent_id = self._path_to_id(parent_path)
        folder_id = self._generate_id()
        now = self._now()
        self._virtual_fs[folder_id] = {
            "id": folder_id,
            "name": name,
            "mime_type": "application/vnd.google-apps.folder",
            "size": 0,
            "created_time": now,
            "modified_time": now,
            "description": "",
            "file_extension": "",
            "parent": parent_id,
        }
        return {"folder_id": folder_id, "name": name, "status": "created"}

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        return {"status": "success", "app": app_name, "message": f"Launched {app_name} on {self.provider}"}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "send_text not supported for DriveDevice"}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        return {"status": "success", "verification": f"{app_name} is running", "app": app_name}
