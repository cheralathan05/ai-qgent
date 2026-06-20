"""AppLaunchService - Dynamic app launch with monkey, am start, and verification."""

import asyncio
import logging
from typing import Any, Dict, Optional

from .adb_service import get_adb_service
from .app_resolver import get_app_resolver

logger = logging.getLogger(__name__)


class AppLaunchResult:
    """Result of an app launch attempt."""

    def __init__(
        self,
        success: bool = False,
        package: Optional[str] = None,
        launch_method: Optional[str] = None,
        verification: Optional[str] = None,
        foreground_app: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.package = package
        self.launch_method = launch_method
        self.verification = verification
        self.foreground_app = foreground_app
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "package": self.package,
            "launch_method": self.launch_method,
            "verification": self.verification,
            "foreground_app": self.foreground_app,
            "error": self.error,
        }


class AppLaunchService:
    """Launches Android apps dynamically with activity resolution and verification.

    Never uses hardcoded activities. Always resolves dynamically.
    """

    def __init__(self, adb_service=None, resolver=None):
        self.adb = adb_service or get_adb_service()
        self.resolver = resolver or get_app_resolver()

    async def resolve_activity(self, device_id: str, package: str) -> Optional[str]:
        """Resolve the launch activity for a package dynamically via ADB."""
        try:
            output = await self.adb.shell(
                device_id,
                f"cmd package resolve-activity --brief {package}",
            )
            for line in output.splitlines():
                line = line.strip()
                if line and ("/" in line) and (package in line or line.startswith(".")):
                    if line.startswith("."):
                        return f"{package}{line}"
                    return line
            return None
        except Exception as e:
            logger.debug(f"Activity resolution for {package} failed: {e}")
            return None

    async def launch_app(self, device_id: str, app_name: str) -> AppLaunchResult:
        """Launch an app by name with full dynamic resolution and verification."""
        await self.resolver.ensure_registry(device_id)

        app_info = self.resolver.resolve_with_info(app_name)
        if not app_info:
            result = AppLaunchResult(
                success=False,
                error=f"App '{app_name}' not found on device",
                verification="not_found",
            )
            return result

        package = app_info.package_name
        launch_method = None
        launch_error = None

        activity = await self.resolve_activity(device_id, package)
        logger.info(f"Resolved activity for {package}: {activity}")

        if activity:
            try:
                activity_part = activity
                if "/" in activity:
                    activity_part = activity.split("/", 1)[1]
                    if activity_part.startswith("."):
                        activity_part = f"{package}{activity_part}"

                await self.adb.start_activity(device_id, package, activity_part)
                launch_method = "am_start_activity"
                logger.info(f"Launched {package} via am start -n {package}/{activity_part}")
            except Exception as e:
                launch_error = e
                logger.debug(f"am start activity failed for {package}: {e}")

        if not activity or launch_error is not None:
            launch_error = None
            try:
                await self.adb.monkey_launch(device_id, package)
                launch_method = "monkey"
                logger.info(f"Launched {package} via monkey")
            except Exception as e:
                launch_error = e
                logger.debug(f"Monkey launch failed for {package}: {e}")
                try:
                    await self.adb.shell(
                        device_id,
                        f"am start -p {package} -a android.intent.action.MAIN -c android.intent.category.LAUNCHER",
                    )
                    launch_method = "am_start_intent"
                    launch_error = None
                    logger.info(f"Launched {package} via am start intent")
                except Exception as e2:
                    launch_error = e2
                    logger.error(f"All launch methods failed for {package}: {e2}")

        await asyncio.sleep(2)

        verification_status = await self._verify_launch(device_id, package)

        if verification_status == "completed":
            return AppLaunchResult(
                success=True,
                package=package,
                launch_method=launch_method,
                verification="completed",
                foreground_app=await self.adb.get_foreground_app(device_id),
            )
        else:
            return AppLaunchResult(
                success=launch_error is None,
                package=package,
                launch_method=launch_method,
                verification=verification_status,
                foreground_app=await self.adb.get_foreground_app(device_id),
                error=str(launch_error) if launch_error else None,
            )

    async def _verify_launch(self, device_id: str, target_package: str) -> str:
        """Verify that the target app is now in the foreground."""
        try:
            foreground = await self.adb.get_foreground_app(device_id)
            if foreground and (
                foreground == target_package or foreground.startswith(target_package)
            ):
                return "completed"

            await asyncio.sleep(2)
            foreground = await self.adb.get_foreground_app(device_id)
            if foreground and (
                foreground == target_package or foreground.startswith(target_package)
            ):
                return "completed"

            return "verification_failed"
        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            return "verification_failed"

    async def force_stop_app(self, device_id: str, app_name: str) -> Dict[str, Any]:
        """Force stop an app."""
        await self.resolver.ensure_registry(device_id)
        app_info = self.resolver.resolve_with_info(app_name)
        package = app_info.package_name if app_info else app_name

        try:
            await self.adb.shell(device_id, f"am force-stop {package}")
            return {"success": True, "package": package}
        except Exception as e:
            return {"success": False, "error": str(e)}


_app_launch_service = None


def get_app_launch_service(adb_service=None, resolver=None) -> AppLaunchService:
    global _app_launch_service
    if _app_launch_service is None:
        _app_launch_service = AppLaunchService(
            adb_service=adb_service, resolver=resolver
        )
    elif adb_service is not None:
        _app_launch_service.adb = adb_service
    elif resolver is not None:
        _app_launch_service.resolver = resolver
    return _app_launch_service
