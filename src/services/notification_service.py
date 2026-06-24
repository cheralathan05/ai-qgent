"""
APA-OS Notification Service
Push notifications, alerts, and in-app notifications
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class NotificationService:
    """Complete notification service"""

    def __init__(self):
        self._subscribers: Dict[str, List] = {}  # user_id -> [callback]

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    def create_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        notification_type: str = "info",
        category: str = None,
        device_id: str = None,
        data: Dict[str, Any] = None,
    ) -> str:
        """Create a new notification"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord
            import uuid

            notif_id = str(uuid.uuid4())
            notification = NotificationRecord(
                id=notif_id,
                user_id=user_id,
                device_id=device_id,
                title=title,
                body=body,
                notification_type=notification_type,
                category=category,
                data=data or {},
            )
            db.add(notification)
            db.commit()

            # Notify subscribers
            self._notify_subscribers(user_id, {
                "id": notif_id,
                "title": title,
                "body": body,
                "type": notification_type,
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
            })

            logger.info(f"Notification created: {notif_id} for user {user_id}")
            return notif_id
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create notification: {e}")
            return ""
        finally:
            db.close()

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
        category: str = None,
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord

            query = db.query(NotificationRecord).filter(
                NotificationRecord.user_id == user_id,
            )

            if unread_only:
                query = query.filter(NotificationRecord.is_read == False)
            if category:
                query = query.filter(NotificationRecord.category == category)

            notifications = query.order_by(
                NotificationRecord.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "body": n.body,
                    "type": n.notification_type,
                    "category": n.category,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ]
        finally:
            db.close()

    def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord

            notification = db.query(NotificationRecord).filter(
                NotificationRecord.id == notification_id,
                NotificationRecord.user_id == user_id,
            ).first()

            if not notification:
                return False

            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()

    def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord

            count = db.query(NotificationRecord).filter(
                NotificationRecord.user_id == user_id,
                NotificationRecord.is_read == False,
            ).update({"is_read": True, "read_at": datetime.utcnow()})
            db.commit()
            return count
        except Exception as e:
            db.rollback()
            return 0
        finally:
            db.close()

    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord

            return db.query(NotificationRecord).filter(
                NotificationRecord.user_id == user_id,
                NotificationRecord.is_read == False,
            ).count()
        finally:
            db.close()

    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        db = self._get_db()
        try:
            from database.auth_models import NotificationRecord

            notification = db.query(NotificationRecord).filter(
                NotificationRecord.id == notification_id,
                NotificationRecord.user_id == user_id,
            ).first()

            if not notification:
                return False

            db.delete(notification)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()

    # ==================== Real-time Subscriptions ====================

    def subscribe(self, user_id: str, callback):
        """Subscribe to real-time notifications"""
        self._subscribers.setdefault(user_id, []).append(callback)

    def unsubscribe(self, user_id: str, callback):
        """Unsubscribe from real-time notifications"""
        if user_id in self._subscribers:
            self._subscribers[user_id] = [
                cb for cb in self._subscribers[user_id] if cb != callback
            ]

    def _notify_subscribers(self, user_id: str, notification: Dict[str, Any]):
        """Notify all subscribers"""
        for callback in self._subscribers.get(user_id, []):
            try:
                callback(notification)
            except Exception as e:
                logger.warning(f"Notification subscriber error: {e}")

    # ==================== Convenience Methods ====================

    def notify_auth_event(self, user_id: str, event_type: str, details: str):
        """Send authentication notification"""
        titles = {
            "login": "New Login",
            "signup": "Welcome to APA-OS",
            "password_reset": "Password Reset",
            "email_verified": "Email Verified",
        }
        self.create_notification(
            user_id=user_id,
            title=titles.get(event_type, "Auth Event"),
            body=details,
            notification_type="info",
            category="auth",
        )

    def notify_device_event(self, user_id: str, device_id: str, event_type: str, details: str):
        """Send device notification"""
        titles = {
            "connected": "Device Connected",
            "disconnected": "Device Disconnected",
            "paired": "Device Paired",
            "trusted": "Device Trusted",
            "low_battery": "Low Battery",
        }
        self.create_notification(
            user_id=user_id,
            device_id=device_id,
            title=titles.get(event_type, "Device Event"),
            body=details,
            notification_type="warning" if event_type == "low_battery" else "info",
            category="device",
        )

    def notify_automation_event(self, user_id: str, rule_name: str, result: str):
        """Send automation notification"""
        self.create_notification(
            user_id=user_id,
            title=f"Automation: {rule_name}",
            body=result,
            notification_type="info",
            category="automation",
        )

    def notify_system_event(self, user_id: str, title: str, body: str, ntype: str = "info"):
        """Send system notification"""
        self.create_notification(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=ntype,
            category="system",
        )


# ==================== Singleton ====================

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
