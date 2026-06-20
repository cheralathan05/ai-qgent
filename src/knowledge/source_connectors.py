"""Knowledge Source Connectors for Phase 3."""

import asyncio
import logging
import os
import json
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SourceDocument:
    id: str
    source_type: str
    source_name: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str = ""
    chunks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SyncResult:
    source_type: str
    source_name: str
    total_files: int = 0
    new_files: int = 0
    updated_files: int = 0
    deleted_files: int = 0
    errors: List[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)


class KnowledgeSourceConnector(ABC):
    def __init__(self, name: str, source_type: str):
        self.name = name
        self.source_type = source_type
        self._connected = False
        self._config: Dict[str, Any] = {}

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def disconnect(self): ...

    @abstractmethod
    async def list_files(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def read_file(self, file_id: str) -> Optional[SourceDocument]: ...

    @abstractmethod
    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult: ...

    @property
    def is_connected(self) -> bool:
        return self._connected


class LocalFileConnector(KnowledgeSourceConnector):
    def __init__(self, name: str = "local", base_paths: Optional[List[str]] = None):
        super().__init__(name, "local_files")
        self.base_paths = base_paths or []
        self._file_cache: Dict[str, Dict[str, Any]] = {}
        self._checksum_cache: Dict[str, str] = {}

    async def connect(self) -> bool:
        valid_paths = []
        for bp in self.base_paths:
            expanded = os.path.expanduser(bp)
            if os.path.exists(expanded):
                valid_paths.append(expanded)
                logger.info(f"Local connector watching: {expanded}")
        self.base_paths = valid_paths
        self._connected = len(valid_paths) > 0
        return self._connected

    async def disconnect(self):
        self._connected = False
        self._file_cache.clear()

    async def list_files(self) -> List[Dict[str, Any]]:
        files = []
        for base in self.base_paths:
            for root, dirs, filenames in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in filenames:
                    fpath = os.path.join(root, fname)
                    try:
                        stat = os.stat(fpath)
                        fhash = self._compute_hash(fpath)
                        files.append({
                            "id": fhash,
                            "file_path": fpath,
                            "file_name": fname,
                            "file_size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "source_type": "local_files",
                            "source_name": self.name,
                            "mime_type": self._guess_mime(fname),
                        })
                    except OSError:
                        continue
        return files

    async def read_file(self, file_id: str) -> Optional[SourceDocument]:
        for base in self.base_paths:
            for root, dirs, filenames in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in filenames:
                    fpath = os.path.join(root, fname)
                    fhash = self._compute_hash(fpath)
                    if fhash == file_id:
                        return await self._read_file_content(fpath, fname)
        return None

    async def read_file_by_path(self, file_path: str) -> Optional[SourceDocument]:
        if os.path.exists(file_path):
            fname = os.path.basename(file_path)
            return await self._read_file_content(file_path, fname)
        return None

    async def _read_file_content(self, fpath: str, fname: str) -> Optional[SourceDocument]:
        try:
            stat = os.stat(fpath)
            with open(fpath, 'rb') as f:
                raw = f.read()
            stat_obj = os.stat(fpath)
            return SourceDocument(
                id=self._compute_hash(fpath),
                source_type="local_files",
                source_name=self.name,
                file_path=fpath,
                file_name=fname,
                file_size=stat_obj.st_size,
                mime_type=self._guess_mime(fname),
                content=raw.decode('utf-8', errors='replace'),
                checksum=self._compute_hash(fpath),
                modified_at=datetime.fromtimestamp(stat_obj.st_mtime),
                metadata={
                    "created": datetime.fromtimestamp(stat_obj.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat_obj.st_mtime).isoformat(),
                    "size": stat_obj.st_size,
                    "extension": os.path.splitext(fname)[1],
                },
            )
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")
            return None

    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult:
        result = SyncResult(source_type="local_files", source_name=self.name)
        current_files: Dict[str, Dict[str, Any]] = {}
        for base in self.base_paths:
            for root, dirs, filenames in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in filenames:
                    fpath = os.path.join(root, fname)
                    try:
                        stat = os.stat(fpath)
                        fhash = self._compute_hash(fpath)
                        current_files[fhash] = {
                            "path": fpath, "name": fname,
                            "size": stat.st_size,
                            "mtime": datetime.fromtimestamp(stat.st_mtime),
                        }
                        result.total_files += 1
                        if fhash not in self._file_cache:
                            result.new_files += 1
                        elif self._file_cache[fhash].get("mtime") != current_files[fhash]["mtime"]:
                            result.updated_files += 1
                    except OSError:
                        continue
        deleted = set(self._file_cache.keys()) - set(current_files.keys())
        result.deleted_files = len(deleted)
        self._file_cache = current_files
        result.completed_at = datetime.utcnow()
        return result

    def _compute_hash(self, fpath: str) -> str:
        try:
            with open(fpath, 'rb') as f:
                return hashlib.md5(f.read(8192)).hexdigest()
        except Exception:
            return hashlib.md5(fpath.encode()).hexdigest()

    def _guess_mime(self, fname: str) -> str:
        ext = os.path.splitext(fname)[1].lower()
        mapping = {
            '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain', '.md': 'text/markdown', '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.json': 'application/json', '.xml': 'application/xml', '.html': 'text/html',
            '.py': 'text/x-python', '.js': 'text/javascript', '.ts': 'text/typescript',
            '.java': 'text/x-java', '.sql': 'text/x-sql',
        }
        return mapping.get(ext, 'application/octet-stream')


class GitHubConnector(KnowledgeSourceConnector):
    def __init__(self, name: str = "github", token: str = "", repos: Optional[List[str]] = None):
        super().__init__(name, "github")
        self.token = token
        self.repos = repos or []
        self._api_base = "https://api.github.com"

    async def connect(self) -> bool:
        if not self.token:
            logger.warning("GitHub connector: no token provided")
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._api_base}/user",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                self._connected = resp.status_code == 200
                if self._connected:
                    logger.info(f"GitHub connected: {resp.json().get('login')}")
                return self._connected
        except Exception as e:
            logger.error(f"GitHub connect failed: {e}")
            return False

    async def disconnect(self):
        self._connected = False

    async def list_files(self) -> List[Dict[str, Any]]:
        files = []
        for repo in self.repos:
            try:
                repo_files = await self._list_repo_files(repo)
                files.extend(repo_files)
            except Exception as e:
                logger.error(f"GitHub list files for {repo}: {e}")
        return files

    async def _list_repo_files(self, repo: str) -> List[Dict[str, Any]]:
        import httpx
        files = []
        async with httpx.AsyncClient() as client:
            contents_url = f"{self._api_base}/repos/{repo}/git/trees/HEAD?recursive=1"
            resp = await client.get(
                contents_url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
            )
            if resp.status_code != 200:
                return files
            data = resp.json()
            for item in data.get("tree", []):
                if item["type"] == "blob":
                    fname = item["path"].split("/")[-1]
                    files.append({
                        "id": item["sha"],
                        "file_path": item["path"],
                        "file_name": fname,
                        "file_size": item.get("size", 0),
                        "source_type": "github",
                        "source_name": f"github/{repo}",
                        "mime_type": self._guess_mime(fname),
                        "repo": repo,
                        "url": item.get("url", ""),
                    })
        return files

    async def read_file(self, file_id: str) -> Optional[SourceDocument]:
        return None

    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult:
        result = SyncResult(source_type="github", source_name=self.name)
        files = await self.list_files()
        result.total_files = len(files)
        result.new_files = len(files)
        result.completed_at = datetime.utcnow()
        return result

    def _guess_mime(self, fname: str) -> str:
        ext = os.path.splitext(fname)[1].lower()
        mapping = {
            '.py': 'text/x-python', '.js': 'text/javascript', '.ts': 'text/typescript',
            '.java': 'text/x-java', '.md': 'text/markdown', '.json': 'application/json',
            '.yml': 'application/x-yaml', '.yaml': 'application/x-yaml',
            '.sql': 'text/x-sql', '.html': 'text/html', '.css': 'text/css',
            '.txt': 'text/plain', '.csv': 'text/csv',
        }
        return mapping.get(ext, 'application/octet-stream')


class GoogleDriveConnector(KnowledgeSourceConnector):
    def __init__(self, name: str = "google_drive", credentials: Dict[str, Any] = None):
        super().__init__(name, "google_drive")
        self.credentials = credentials or {}

    async def connect(self) -> bool:
        if not self.credentials:
            logger.warning("Google Drive connector: no credentials")
            return False
        self._connected = True
        return True

    async def disconnect(self):
        self._connected = False

    async def list_files(self) -> List[Dict[str, Any]]:
        return []

    async def read_file(self, file_id: str) -> Optional[SourceDocument]:
        return None

    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult:
        return SyncResult(source_type="google_drive", source_name=self.name)


class NotionConnector(KnowledgeSourceConnector):
    def __init__(self, name: str = "notion", api_key: str = "", database_ids: Optional[List[str]] = None):
        super().__init__(name, "notion")
        self.api_key = api_key
        self.database_ids = database_ids or []

    async def connect(self) -> bool:
        if not self.api_key:
            logger.warning("Notion connector: no API key")
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.notion.com/v1/users/me",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Notion-Version": "2022-06-28",
                    },
                    timeout=10,
                )
                self._connected = resp.status_code == 200
                if self._connected:
                    logger.info("Notion connected")
                return self._connected
        except Exception as e:
            logger.error(f"Notion connect failed: {e}")
            return False

    async def disconnect(self):
        self._connected = False

    async def list_files(self) -> List[Dict[str, Any]]:
        return []

    async def read_file(self, file_id: str) -> Optional[SourceDocument]:
        return None

    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult:
        return SyncResult(source_type="notion", source_name=self.name)


class SlackConnector(KnowledgeSourceConnector):
    def __init__(self, name: str = "slack", token: str = "", channels: Optional[List[str]] = None):
        super().__init__(name, "slack")
        self.token = token
        self.channels = channels or []

    async def connect(self) -> bool:
        if not self.token:
            logger.warning("Slack connector: no token")
            return False
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                self._connected = resp.status_code == 200 and resp.json().get("ok")
                return self._connected
        except Exception as e:
            logger.error(f"Slack connect failed: {e}")
            return False

    async def disconnect(self):
        self._connected = False

    async def list_files(self) -> List[Dict[str, Any]]:
        return []

    async def read_file(self, file_id: str) -> Optional[SourceDocument]:
        return None

    async def sync(self, last_sync: Optional[datetime] = None) -> SyncResult:
        return SyncResult(source_type="slack", source_name=self.name)


_connectors: Dict[str, KnowledgeSourceConnector] = {}


def get_source_connector(source_type: str) -> Optional[KnowledgeSourceConnector]:
    return _connectors.get(source_type)


def get_all_connectors() -> List[KnowledgeSourceConnector]:
    return list(_connectors.values())


def register_connector(connector: KnowledgeSourceConnector):
    _connectors[connector.source_type] = connector
    logger.info(f"Registered source connector: {connector.source_type}/{connector.name}")


def _init_default_connectors():
    user_paths = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
    ]
    local = LocalFileConnector("local", base_paths=user_paths)
    register_connector(local)

_defaults_initialized = False


def ensure_default_connectors():
    global _defaults_initialized
    if not _defaults_initialized:
        _init_default_connectors()
        _defaults_initialized = True
