"""Device targeting rules for APA-OS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from devices import AndroidDevice, WindowsDevice, device_manager


PHONE_HINTS = (
    "phone",
    "android",
    "mobile",
    "cell",
    "smartphone",
    "my phone",
    "on my phone",
)

WINDOWS_HINTS = (
    "laptop",
    "windows",
    "pc",
    "computer",
    "desktop",
    "on my laptop",
)


@dataclass
class DeviceSelection:
    """Resolved execution target for a command."""

    target_device: str
    device_id: Optional[str]
    device_type: Optional[str]
    display_name: str
    available: bool = True
    explicit: bool = False
    source: str = "default"
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "target_device": self.target_device,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "display_name": self.display_name,
            "available": self.available,
            "explicit": self.explicit,
            "source": self.source,
            "reason": self.reason,
        }


class DeviceSelector:
    """Pick the best device for a command.

    Priority:
    1. Explicit user request in the command text.
    2. Preserve the current conversation device when possible.
    3. Android first.
    4. Windows only when Android is unavailable.
    """

    def _get_android_devices(self):
        return [device for device in device_manager.list_devices() if isinstance(device, AndroidDevice)]

    def _get_windows_devices(self):
        return [device for device in device_manager.list_devices() if isinstance(device, WindowsDevice)]

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    @staticmethod
    def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
        return any(hint in text for hint in hints)

    def _build_selection(
        self,
        *,
        target_device: str,
        device_id: Optional[str],
        device_type: Optional[str],
        display_name: str,
        available: bool,
        explicit: bool,
        source: str,
        reason: str,
    ) -> DeviceSelection:
        return DeviceSelection(
            target_device=target_device,
            device_id=device_id,
            device_type=device_type,
            display_name=display_name,
            available=available,
            explicit=explicit,
            source=source,
            reason=reason,
        )

    def select_device(
        self,
        command: str,
        *,
        preferred_device_id: Optional[str] = None,
        session_device_id: Optional[str] = None,
    ) -> DeviceSelection:
        normalized = self._normalize_text(command)

        explicit_phone = self._contains_any(normalized, PHONE_HINTS)
        explicit_windows = self._contains_any(normalized, WINDOWS_HINTS)

        if explicit_phone and not explicit_windows:
            return self._select_android(explicit=True, reason="explicit phone request")

        if explicit_windows and not explicit_phone:
            return self._select_windows(explicit=True, reason="explicit laptop request")

        if session_device_id:
            session_device = device_manager.get_device(session_device_id)
            if isinstance(session_device, AndroidDevice):
                return self._build_selection(
                    target_device="android",
                    device_id=session_device.device_id,
                    device_type="android",
                    display_name="phone",
                    available=True,
                    explicit=False,
                    source="session",
                    reason="continue on the current phone",
                )
            if isinstance(session_device, WindowsDevice):
                windows_devices = self._get_windows_devices()
                if windows_devices:
                    return self._build_selection(
                        target_device="windows",
                        device_id=windows_devices[0].device_id,
                        device_type="windows",
                        display_name="laptop",
                        available=True,
                        explicit=False,
                        source="session",
                        reason="continue on the current laptop",
                    )

        if preferred_device_id:
            preferred_device = device_manager.get_device(preferred_device_id)
            if isinstance(preferred_device, AndroidDevice):
                return self._build_selection(
                    target_device="android",
                    device_id=preferred_device.device_id,
                    device_type="android",
                    display_name="phone",
                    available=True,
                    explicit=False,
                    source="preferred",
                    reason="preferred device is an Android phone",
                )
            if isinstance(preferred_device, WindowsDevice):
                return self._build_selection(
                    target_device="windows",
                    device_id=preferred_device.device_id,
                    device_type="windows",
                    display_name="laptop",
                    available=True,
                    explicit=False,
                    source="preferred",
                    reason="preferred device is a Windows laptop",
                )

        return self._select_android_or_windows()

    def _select_android(self, *, explicit: bool, reason: str) -> DeviceSelection:
        android_devices = self._get_android_devices()
        if android_devices:
            device = android_devices[0]
            return self._build_selection(
                target_device="android",
                device_id=device.device_id,
                device_type="android",
                display_name="phone",
                available=True,
                explicit=explicit,
                source="explicit" if explicit else "default",
                reason=reason,
            )

        return self._build_selection(
            target_device="android",
            device_id=None,
            device_type="android",
            display_name="phone",
            available=False,
            explicit=explicit,
            source="explicit" if explicit else "default",
            reason="android device is unavailable",
        )

    def _select_windows(self, *, explicit: bool, reason: str) -> DeviceSelection:
        windows_devices = self._get_windows_devices()
        if windows_devices:
            device = windows_devices[0]
            return self._build_selection(
                target_device="windows",
                device_id=device.device_id,
                device_type="windows",
                display_name="laptop",
                available=True,
                explicit=explicit,
                source="explicit" if explicit else "default",
                reason=reason,
            )

        return self._build_selection(
            target_device="windows",
            device_id=None,
            device_type="windows",
            display_name="laptop",
            available=False,
            explicit=explicit,
            source="explicit" if explicit else "default",
            reason="windows device is unavailable",
        )

    def _select_android_or_windows(self) -> DeviceSelection:
        android_devices = self._get_android_devices()
        if android_devices:
            device = android_devices[0]
            return self._build_selection(
                target_device="android",
                device_id=device.device_id,
                device_type="android",
                display_name="phone",
                available=True,
                explicit=False,
                source="default",
                reason="android is the default execution target",
            )

        windows_devices = self._get_windows_devices()
        if windows_devices:
            device = windows_devices[0]
            return self._build_selection(
                target_device="windows",
                device_id=device.device_id,
                device_type="windows",
                display_name="laptop",
                available=True,
                explicit=False,
                source="fallback",
                reason="android unavailable, falling back to windows",
            )

        return self._build_selection(
            target_device="unknown",
            device_id=None,
            device_type=None,
            display_name="device",
            available=False,
            explicit=False,
            source="none",
            reason="no registered devices were found",
        )


device_selector = None


def get_device_selector() -> DeviceSelector:
    global device_selector
    if device_selector is None:
        device_selector = DeviceSelector()
    return device_selector