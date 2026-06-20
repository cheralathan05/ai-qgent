"""File Explorer for Phase 3 - Browse, Search, Preview Files."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from knowledge.source_connectors import LocalFileConnector, SourceDocument

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    extension: str
    modified_at: str
    created_at: str
    is_directory: bool = False
    is_favorite: bool = False
    source_type: str = "local"
    preview: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileExplorer:
    def __init__(self):
        self._connector = LocalFileConnector("explorer")
        self._favorites: Set[str] = set()
        self._recent: List[str] = []
        self._max_recent = 50

    async def browse(self, path: str = "") -> List[FileInfo]:
        base = path or os.path.expanduser("~")
        items = []
        try:
            entries = os.listdir(base)
            for entry in entries:
                full_path = os.path.join(base, entry)
                try:
                    stat = os.stat(full_path)
                    is_dir = os.path.isdir(full_path)
                    ext = os.path.splitext(entry)[1].lower()
                    items.append(FileInfo(
                        id=full_path,
                        name=entry,
                        path=full_path,
                        size=stat.st_size if not is_dir else 0,
                        mime_type="directory" if is_dir else self._guess_mime(ext),
                        extension=ext,
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        is_directory=is_dir,
                        is_favorite=full_path in self._favorites,
                    ))
                except OSError:
                    continue
        except Exception as e:
            logger.error(f"Browse failed for {base}: {e}")
        items.sort(key=lambda x: (not x.is_directory, x.name.lower()))
        return items

    async def search_files(self, query: str, path: str = "") -> List[FileInfo]:
        base = path or os.path.expanduser("~")
        results = []
        q = query.lower()
        try:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in files:
                    if q in fname.lower():
                        full_path = os.path.join(root, fname)
                        try:
                            stat = os.stat(full_path)
                            ext = os.path.splitext(fname)[1].lower()
                            results.append(FileInfo(
                                id=full_path, name=fname, path=full_path,
                                size=stat.st_size, mime_type=self._guess_mime(ext),
                                extension=ext,
                                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            ))
                        except OSError:
                            continue
                if len(results) >= 100:
                    break
        except Exception as e:
            logger.error(f"Search failed: {e}")
        return results[:100]

    async def get_recent(self, limit: int = 20) -> List[FileInfo]:
        files = []
        for fpath in self._recent[-limit:]:
            if os.path.exists(fpath):
                try:
                    stat = os.stat(fpath)
                    fname = os.path.basename(fpath)
                    ext = os.path.splitext(fname)[1].lower()
                    files.append(FileInfo(
                        id=fpath, name=fname, path=fpath,
                        size=stat.st_size, mime_type=self._guess_mime(ext),
                        extension=ext,
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    ))
                except OSError:
                    continue
        return files

    async def get_favorites(self) -> List[FileInfo]:
        files = []
        for fpath in self._favorites:
            if os.path.exists(fpath):
                try:
                    stat = os.stat(fpath)
                    fname = os.path.basename(fpath)
                    ext = os.path.splitext(fname)[1].lower()
                    files.append(FileInfo(
                        id=fpath, name=fname, path=fpath,
                        size=stat.st_size, mime_type=self._guess_mime(ext),
                        extension=ext,
                        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        is_favorite=True,
                    ))
                except OSError:
                    continue
        return files

    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        if os.path.exists(file_id):
            try:
                stat = os.stat(file_id)
                fname = os.path.basename(file_id)
                ext = os.path.splitext(fname)[1].lower()
                return FileInfo(
                    id=file_id, name=fname, path=file_id,
                    size=stat.st_size, mime_type=self._guess_mime(ext),
                    extension=ext,
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    is_favorite=file_id in self._favorites,
                )
            except OSError:
                pass
        return None

    async def read_file(self, file_path: str) -> Optional[SourceDocument]:
        doc = await self._connector.read_file_by_path(file_path)
        if doc:
            self._add_recent(file_path)
        return doc

    def add_favorite(self, file_path: str):
        self._favorites.add(file_path)

    def remove_favorite(self, file_path: str):
        self._favorites.discard(file_path)

    def _add_recent(self, file_path: str):
        if file_path in self._recent:
            self._recent.remove(file_path)
        self._recent.append(file_path)
        if len(self._recent) > self._max_recent:
            self._recent = self._recent[-self._max_recent:]

    def _guess_mime(self, ext: str) -> str:
        mapping = {
            '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain', '.md': 'text/markdown', '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.json': 'application/json', '.xml': 'application/xml', '.html': 'text/html',
            '.py': 'text/x-python', '.js': 'text/javascript', '.ts': 'text/typescript',
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif',
            '.mp4': 'video/mp4', '.mp3': 'audio/mpeg', '.zip': 'application/zip',
        }
        return mapping.get(ext, 'application/octet-stream')


_file_explorer: Optional[FileExplorer] = None


def get_file_explorer() -> FileExplorer:
    global _file_explorer
    if _file_explorer is None:
        _file_explorer = FileExplorer()
    return _file_explorer
