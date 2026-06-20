"""AndroidAppResolver - Dynamic app resolution with fuzzy, partial, and alias matching."""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from difflib import SequenceMatcher

from .app_discovery import AppInfo, get_app_discovery_service

logger = logging.getLogger(__name__)


class AndroidAppResolver:
    """Resolves natural language app names to Android package names dynamically.

    No hardcoded mappings. Discovers apps via ADB and provides:
    - Exact matching
    - Fuzzy matching (Levenshtein-like)
    - Partial matching
    - Alias matching (auto-generated from package names and labels)
    - Search by query
    """

    def __init__(self, discovery_service=None):
        self._discovery = discovery_service or get_app_discovery_service()
        self._registry: Dict[str, AppInfo] = {}
        self._aliases: Dict[str, str] = {}
        self._package_map: Dict[str, AppInfo] = {}
        self._last_device_id: Optional[str] = None
        self._ready = False

    @property
    def registry(self) -> Dict[str, AppInfo]:
        return self._registry

    @property
    def package_map(self) -> Dict[str, AppInfo]:
        return self._package_map

    async def ensure_registry(self, device_id: str) -> None:
        """Ensure the registry is built for the given device."""
        if self._ready and self._last_device_id == device_id:
            return
        await self.build_registry(device_id)

    async def build_registry(self, device_id: str) -> None:
        """Scan all installed apps and build the resolution registry."""
        apps = await self._discovery.scan_installed_apps(device_id)

        self._registry.clear()
        self._aliases.clear()
        self._package_map.clear()

        for app in apps:
            self._package_map[app.package_name] = app

            for name in app.normalized_names:
                clean_name = name.strip().lower()
                if clean_name:
                    if clean_name not in self._registry:
                        self._registry[clean_name] = app
                    self._add_alias(clean_name, app.package_name)

            primary_name = app.app_label.strip().lower()
            if primary_name and primary_name not in self._registry:
                self._registry[primary_name] = app
                self._add_alias(primary_name, app.package_name)

            package_lower = app.package_name.lower()
            parts = package_lower.split(".")
            for part in parts:
                if part and len(part) > 2 and part not in {"com", "org", "net", "io", "co", "app", "android", "google", "mobile", "imobile"}:
                    if part not in self._registry:
                        self._registry[part] = app
                        self._add_alias(part, app.package_name)

        self._last_device_id = device_id
        self._ready = True
        logger.info(f"App registry built: {len(self._registry)} names, {len(apps)} apps")

    def _add_alias(self, name: str, package: str) -> None:
        """Add an alias mapping."""
        if name not in self._aliases:
            self._aliases[name] = package

    def resolve(self, app_name: str) -> Optional[str]:
        """Resolve a natural language app name to a package name.

        Attempts in order:
        1. Exact match
        2. Alias match
        3. Partial match
        4. Fuzzy match
        """
        if not app_name:
            return None

        search = app_name.strip().lower()

        result = self._exact_match(search)
        if result:
            return result

        result = self._partial_match(search)
        if result:
            return result

        result = self._fuzzy_match(search)
        if result:
            return result

        return None

    def resolve_with_info(self, app_name: str) -> Optional[AppInfo]:
        """Resolve app name and return full AppInfo."""
        package = self.resolve(app_name)
        if package:
            return self._package_map.get(package)
        return None

    def _exact_match(self, search: str) -> Optional[str]:
        """Try exact lookups."""
        if search in self._aliases:
            return self._aliases[search]

        pkg = self._registry.get(search)
        if pkg:
            return pkg.package_name

        if search in self._package_map:
            return search

        return None

    def _partial_match(self, search: str) -> Optional[str]:
        """Try partial matching against all known names and package parts."""
        search_lower = search.lower()

        best_match = None
        best_score = 0.0

        for name, app_info in self._registry.items():
            if search_lower in name:
                score = len(search_lower) / len(name)
                if score > best_score:
                    best_score = score
                    best_match = app_info.package_name

            parts = name.split()
            for part in parts:
                if part.startswith(search_lower) or search_lower.startswith(part):
                    score = len(search_lower) / max(len(part), 1)
                    if score > best_score:
                        best_score = score
                        best_match = app_info.package_name

        for pkg_name in self._package_map:
            pkg_lower = pkg_name.lower()
            if search_lower in pkg_lower:
                score = len(search_lower) / len(pkg_lower)
                if score > best_score:
                    best_score = score
                    best_match = pkg_name

            pkg_parts = pkg_lower.split(".")
            for part in pkg_parts:
                if part.startswith(search_lower):
                    score = len(search_lower) / max(len(part), 1)
                    if score > best_score:
                        best_score = score
                        best_match = pkg_name

        if best_score >= 0.5:
            return best_match

        return None

    def _fuzzy_match(self, search: str) -> Optional[str]:
        """Fuzzy matching using SequenceMatcher."""
        search_lower = search.lower()

        candidates = []
        for name, app_info in self._registry.items():
            ratio = SequenceMatcher(None, search_lower, name).ratio()
            if ratio > 0.5:
                candidates.append((ratio, app_info.package_name))

        for pkg_name in self._package_map:
            pkg_lower = pkg_name.lower()
            ratio = SequenceMatcher(None, search_lower, pkg_lower).ratio()
            if ratio > 0.5:
                candidates.append((ratio, pkg_name))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_match = candidates[0]

        if best_score >= 0.6:
            return best_match

        return None

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search apps by query string (name or package)."""
        query_lower = query.strip().lower()
        if not query_lower:
            return self.list_apps()

        results = []
        for pkg, info in self._package_map.items():
            score = 0
            if query_lower in info.app_label.lower():
                score = max(score, 0.9)
            if query_lower in pkg.lower():
                score = max(score, 0.8)
            for name in info.normalized_names:
                if query_lower in name:
                    score = max(score, 0.85)
                    break

            if score > 0:
                results.append({
                    "package_name": pkg,
                    "app_label": info.app_label,
                    "launch_activity": info.launch_activity,
                    "score": score,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def list_apps(self) -> List[Dict[str, Any]]:
        """List all discovered apps."""
        return [
            {
                "package_name": info.package_name,
                "app_label": info.app_label,
                "launch_activity": info.launch_activity,
                "is_system_app": info.is_system_app,
                "version": info.version,
            }
            for info in sorted(
                self._package_map.values(),
                key=lambda x: x.app_label.lower(),
            )
        ]

    def is_ready(self) -> bool:
        return self._ready

    async def refresh(self, device_id: str) -> None:
        """Force refresh the registry."""
        self._ready = False
        await self.build_registry(device_id)


_app_resolver = None


def get_app_resolver(discovery_service=None) -> AndroidAppResolver:
    global _app_resolver
    if _app_resolver is None:
        _app_resolver = AndroidAppResolver(discovery_service=discovery_service)
    elif discovery_service is not None:
        _app_resolver._discovery = discovery_service
    return _app_resolver
