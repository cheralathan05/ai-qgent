"""AppDiscoveryService - Discovers installed Android apps via ADB."""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class AppInfo:
    package_name: str
    app_label: str
    launch_activity: Optional[str] = None
    is_system_app: bool = False
    install_time: Optional[str] = None
    version: Optional[str] = None
    normalized_names: Set[str] = field(default_factory=set)


class AppDiscoveryService:
    """Discovers installed apps on an Android device via ADB."""

    def __init__(self, adb_service=None):
        self.adb = adb_service
        self._system_packages: Set[str] = set()
        self._package_labels: Dict[str, str] = {}

    async def scan_installed_apps(self, device_id: str) -> List[AppInfo]:
        """Scan all installed apps on the device and return AppInfo list."""
        if not self.adb:
            logger.error("ADB service not available")
            return []

        apps: List[AppInfo] = []

        try:
            all_packages = await self._get_all_packages(device_id)
            system_packages = await self._get_system_packages(device_id)

            for package in all_packages:
                try:
                    info = await self._get_app_info(device_id, package, system_packages)
                    if info:
                        apps.append(info)
                except Exception as e:
                    logger.debug(f"Skipping {package}: {e}")

            logger.info(f"Discovered {len(apps)} installed apps on {device_id}")
        except Exception as e:
            logger.error(f"Failed to scan installed apps: {e}")

        return apps

    async def _get_all_packages(self, device_id: str) -> List[str]:
        """Get all installed package names."""
        try:
            output = await self.adb.shell(device_id, "pm list packages")
            packages = []
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkg = line[len("package:"):].strip()
                    if pkg:
                        packages.append(pkg)
            return sorted(packages)
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            return []

    async def _get_system_packages(self, device_id: str) -> Set[str]:
        """Get set of system package names."""
        try:
            output = await self.adb.shell(device_id, "pm list packages -s")
            system = set()
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkg = line[len("package:"):].strip()
                    if pkg:
                        system.add(pkg)
            return system
        except Exception:
            return set()

    async def _get_app_info(self, device_id: str, package: str, system_packages: Set[str]) -> Optional[AppInfo]:
        """Get info for a single package. Uses heuristic labels (fast, no per-package ADB)."""
        app_label = self._extract_label_from_package(package)

        normalized_names = self._generate_normalized_names(package, app_label)

        return AppInfo(
            package_name=package,
            app_label=app_label,
            launch_activity=None,
            is_system_app=package in system_packages,
            install_time=None,
            version=None,
            normalized_names=normalized_names,
        )

    def _extract_label_from_package(self, package: str) -> str:
        """Derive a human-readable label from the package name."""
        common_suffixes = {"android", "app", "google", "mobile", "imobile"}
        parts = package.split(".")

        # Walk backwards from the last segment to find a non-common label.
        for i in range(len(parts) - 1, -1, -1):
            candidate = parts[i]
            if candidate.lower() not in common_suffixes and len(candidate) > 1:
                label = candidate
                break
        else:
            label = parts[-1] if parts else package

        label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', label)
        label = label.replace("_", " ").replace("-", " ")
        words = [w for w in label.split() if len(w) > 1 or w.isalpha()]
        final_label = " ".join(words).strip() if words else label

        return final_label.title()

    def _generate_normalized_names(self, package: str, label: str) -> Set[str]:
        """Generate various normalized names for matching."""
        names = set()
        label_lower = label.strip().lower()
        if label_lower:
            names.add(label_lower)

        package_lower = package.lower()
        parts = package_lower.split(".")
        if parts:
            last_part = parts[-1]
            names.add(last_part)
            if len(parts) >= 2:
                second_last = parts[-2]
                if second_last != last_part:
                    names.add(second_last)

        clean_label = re.sub(r'[^a-z0-9]', '', label_lower)
        if clean_label and clean_label != label_lower:
            names.add(clean_label)

        short_name = label_lower.split()[0] if label_lower.split() else ""
        if short_name and len(short_name) > 1:
            names.add(short_name)

        acronym = "".join(w[0] for w in label_lower.split() if w)
        if acronym and len(acronym) > 1:
            names.add(acronym)

        for part in parts:
            if part and len(part) > 2 and part not in {"com", "org", "net", "io", "co", "app", "android", "google"}:
                names.add(part)

        return names


_app_discovery_service = None


def get_app_discovery_service(adb_service=None) -> AppDiscoveryService:
    global _app_discovery_service
    if _app_discovery_service is None:
        _app_discovery_service = AppDiscoveryService(adb_service=adb_service)
    elif adb_service is not None:
        _app_discovery_service.adb = adb_service
    return _app_discovery_service
