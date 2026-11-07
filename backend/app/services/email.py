"""Pluggable outbound email, currently used only for password reset.

Disabled unless EMAIL_PROVIDER is set (see app/core/config.py). Providers:
  log   writes a line to the server log; includes the reset link only when
        APP_ENV is dev/development/test/local, never in production.
  smtp  sends through the SMTP_* settings.
A sending failure is logged (without the token) and swallowed, so the request
endpoint answers identically whether or not mail went out.
"""

import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

_DEV_ENVS = {"dev", "development", "test", "local"}


def reset_link(settings, token: str) -> str:
    base = (settings.password_reset_base_url or "").rstrip("/")
    return f"{base}/reset-password?token={token}"


def _message(settings, to: str, link: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.email_from
    msg["To"] = to
    minutes = max(1, settings.password_reset_ttl_seconds // 60)
    msg.set_content(
        "Someone asked to reset the password for this account.\n\n"
        f"Open this link to choose a new password (valid for {minutes} minutes, one use):\n{link}\n\n"
        "If this was not you, ignore this email; your password stays the same."
    )
    return msg


def send_password_reset(settings, to: str, token: str) -> None:
    provider = settings.email_provider.strip().lower()
    link = reset_link(settings, token)
    try:
        if provider == "log":
            if settings.app_env.lower() in _DEV_ENVS:
                logger.info("password reset email (log provider) to=%s link=%s", to, link)
            else:
                logger.info("password reset email (log provider) queued; link withheld outside dev")
        elif provider == "smtp":
            if not (settings.smtp_host and settings.email_from and settings.password_reset_base_url):
                logger.error("smtp email provider is missing SMTP_HOST, EMAIL_FROM or PASSWORD_RESET_BASE_URL")
                return
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(_message(settings, to, link))
        else:
            logger.error("unknown EMAIL_PROVIDER %r; password reset email not sent", provider)
    except Exception:
        logger.exception("password reset email failed to send")
