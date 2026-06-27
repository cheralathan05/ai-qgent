"""
APA-OS Email Service
SMTP-based email sending for verification, password reset, and notifications
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via SMTP"""

    def __init__(self):
        self._config = None

    def _get_config(self):
        if self._config is None:
            from config import Config
            self._config = Config.smtp_config
        return self._config

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send an email via SMTP"""
        cfg = self._get_config()
        if not cfg.user or not cfg.password:
            logger.warning("SMTP not configured — email not sent to %s", to_email)
            return False

        msg = MIMEMultipart("alternative")
        msg["From"] = cfg.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(cfg.host, cfg.port, timeout=15) as server:
                server.ehlo()
                if not cfg.secure:
                    server.starttls(context=ctx)
                    server.ehlo()
                server.login(cfg.user, cfg.password)
                server.sendmail(cfg.from_addr, [to_email], msg.as_string())

            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return False

    def send_password_reset(self, to_email: str, reset_link: str) -> bool:
        """Send password reset email"""
        subject = "Reset your APA-OS password"
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif">
<table width="100%%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#fff;margin:40px 0;border-radius:12px;overflow:hidden">
<tr><td style="padding:40px 32px 0" align="center">
<h1 style="font-size:22px;margin:0 0 8px;color:#1a1a2e">Reset your password</h1>
<p style="font-size:14px;color:#666;margin:0 0 24px;line-height:1.6">
We received a request to reset your APA-OS password.<br>
Click the button below to set a new one.
</p>
<a href="{reset_link}" style="display:inline-block;padding:14px 36px;background:#e6a847;color:#1a1a2e;text-decoration:none;border-radius:8px;font-size:13px;font-weight:bold;letter-spacing:0.5px">
Reset Password
</a>
<p style="font-size:12px;color:#999;margin:32px 0 0;line-height:1.5">
If you didn't request this, you can safely ignore this email.<br>
This link expires in 15 minutes.
</p>
</td></tr></table>
</td></tr></table>
</body>
</html>"""
        text = f"Reset your APA-OS password\n\nClick this link to reset: {reset_link}\n\nThis link expires in 15 minutes."
        return self.send_email(to_email, subject, html, text)

    def send_verification(self, to_email: str, verify_link: str) -> bool:
        """Send email verification link"""
        subject = "Verify your APA-OS email"
        html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif">
<table width="100%%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#fff;margin:40px 0;border-radius:12px;overflow:hidden">
<tr><td style="padding:40px 32px 0" align="center">
<h1 style="font-size:22px;margin:0 0 8px;color:#1a1a2e">Verify your email</h1>
<p style="font-size:14px;color:#666;margin:0 0 24px;line-height:1.6">
Thanks for signing up for APA-OS.<br>
Click the button below to verify your email address.
</p>
<a href="{verify_link}" style="display:inline-block;padding:14px 36px;background:#e6a847;color:#1a1a2e;text-decoration:none;border-radius:8px;font-size:13px;font-weight:bold;letter-spacing:0.5px">
Verify Email
</a>
<p style="font-size:12px;color:#999;margin:32px 0 0;line-height:1.5">
If you didn't create an account, you can safely ignore this email.<br>
This link expires in 24 hours.
</p>
</td></tr></table>
</td></tr></table>
</body>
</html>"""
        text = f"Verify your APA-OS email\n\nClick this link to verify: {verify_link}\n\nThis link expires in 24 hours."
        return self.send_email(to_email, subject, html, text)


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
