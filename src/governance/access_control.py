from __future__ import annotations

from enum import Enum
from typing import Optional


class AccessRole(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    DEVICE_OPERATOR = "device_operator"
    GUEST = "guest"


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    ADMIN = "admin"
    MANAGE_DEVICES = "manage_devices"
    SEND_MESSAGES = "send_messages"
    LAUNCH_APPS = "launch_apps"
    ACCESS_FILES = "access_files"
    MANAGE_USERS = "manage_users"


_ROLE_PERMISSIONS_DEFAULT: dict[AccessRole, set[Permission]] = {
    AccessRole.ADMIN: {
        Permission.READ, Permission.WRITE, Permission.EXECUTE,
        Permission.CONFIGURE, Permission.ADMIN,
        Permission.MANAGE_DEVICES, Permission.SEND_MESSAGES,
        Permission.LAUNCH_APPS, Permission.ACCESS_FILES,
        Permission.MANAGE_USERS,
    },
    AccessRole.USER: {
        Permission.READ, Permission.WRITE, Permission.EXECUTE,
        Permission.CONFIGURE, Permission.SEND_MESSAGES,
        Permission.LAUNCH_APPS, Permission.ACCESS_FILES,
    },
    AccessRole.VIEWER: {
        Permission.READ, Permission.ACCESS_FILES,
    },
    AccessRole.DEVICE_OPERATOR: {
        Permission.READ, Permission.EXECUTE,
        Permission.CONFIGURE, Permission.MANAGE_DEVICES,
        Permission.ACCESS_FILES,
    },
    AccessRole.GUEST: {
        Permission.READ,
    },
}


class AccessControl:
    def __init__(self) -> None:
        self._role_permissions: dict[AccessRole, set[Permission]] = {
            role: perms.copy() for role, perms in _ROLE_PERMISSIONS_DEFAULT.items()
        }

    def check_permission(self, role: AccessRole, permission: Permission) -> bool:
        perms = self._role_permissions.get(role)
        if perms is None:
            return False
        return permission in perms

    def get_role_permissions(self, role: AccessRole) -> list[Permission]:
        return sorted(self._role_permissions.get(role, set()), key=lambda p: p.value)

    def add_role_permission(self, role: AccessRole, permission: Permission) -> None:
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].add(permission)

    def remove_role_permission(self, role: AccessRole, permission: Permission) -> bool:
        perms = self._role_permissions.get(role)
        if perms is None or permission not in perms:
            return False
        perms.discard(permission)
        return True


_instance: Optional[AccessControl] = None


def get_access_control() -> AccessControl:
    global _instance
    if _instance is None:
        _instance = AccessControl()
    return _instance
