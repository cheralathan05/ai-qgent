"""AppDiscoveryService - Discovers installed Android apps via ADB."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

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
        """Get detailed info for a single package."""
        app_label = self._extract_label_from_package(package)

        launch_activity = await self._resolve_activity(device_id, package)
        version = await self._get_app_version(device_id, package)
        install_time = await self._get_install_time(device_id, package)
        is_system = package in system_packages

        try:
            label_from_device = await self._get_app_label(device_id, package)
            if label_from_device:
                app_label = label_from_device
        except Exception:
            pass

        normalized_names = self._generate_normalized_names(package, app_label)

        return AppInfo(
            package_name=package,
            app_label=app_label,
            launch_activity=launch_activity,
            is_system_app=is_system,
            install_time=install_time,
            version=version,
            normalized_names=normalized_names,
        )

    async def _resolve_activity(self, device_id: str, package: str) -> Optional[str]:
        """Resolve launch activity for a package dynamically."""
        try:
            output = await self.adb.shell(
                device_id,
                f"cmd package resolve-activity --brief {package}",
            )
            for line in output.splitlines():
                line = line.strip()
                if "/." in line and package in line:
                    return line
                if line.startswith(package):
                    return line
            return None
        except Exception as e:
            logger.debug(f"Could not resolve activity for {package}: {e}")
            return None

    async def _get_app_label(self, device_id: str, package: str) -> Optional[str]:
        """Get human-readable app label from package dump."""
        try:
            output = await self.adb.shell(
                device_id,
                f"dumpsys package {package}",
            )
            for line in output.splitlines():
                line_lower = line.strip().lower()
                if line_lower.startswith("application-label:"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
                if "application-label:" in line_lower:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        base = parts[1].strip()
                        if base and not base.startswith("application-label"):
                            return base
            return None
        except Exception:
            return None

    async def _get_app_version(self, device_id: str, package: str) -> Optional[str]:
        """Get version name for a package."""
        try:
            output = await self.adb.shell(
                device_id,
                f"dumpsys package {package}",
            )
            match = re.search(r"versionName=([^\s]+)", output)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    async def _get_install_time(self, device_id: str, package: str) -> Optional[str]:
        """Get first install time for a package."""
        try:
            output = await self.adb.shell(
                device_id,
                f"dumpsys package {package}",
            )
            match = re.search(r"firstInstallTime=([^\s]+)", output)
            if match:
                return match.group(1)
            return None
        except Exception:
            return None

    def _extract_label_from_package(self, package: str) -> str:
        """Derive a human-readable label from the package name."""
        parts = package.split(".")
        if len(parts) >= 2:
            label = parts[-1]
        else:
            label = package

        label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', label)
        label = label.replace("_", " ").replace("-", " ")
        words = label.split()
        meaningful_words = [w for w in words if len(w) > 1 or w.isalpha()]
        if not meaningful_words:
            meaningful_words = [label]

        final_label = " ".join(meaningful_words).strip()

        common_suffixes = [
            "android", "app", "google", "mobile", "imobile",
        ]
        words = final_label.split()
        filtered = [w for w in words if w.lower() not in common_suffixes]
        if filtered:
            final_label = " ".join(filtered)

        if not final_label:
            final_label = parts[-2] if len(parts) >= 2 else package

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
