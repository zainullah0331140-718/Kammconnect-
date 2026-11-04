import logging
import smtplib
from email.message import EmailMessage
from html import escape

from app.core.config import settings

logger = logging.getLogger("kaamconnect.email")


def send_password_reset_email(
    *, to_email: str, full_name: str, reset_url: str
) -> bool:
    if not settings.smtp_host:
        if not settings.is_production:
            logger.info("Password reset link for %s: %s", to_email, reset_url)
        else:
            logger.error(
                "SMTP is not configured; password reset email for %s was not sent.",
                to_email,
            )
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your KaamConnect password"
    message["From"] = settings.smtp_from
    message["To"] = to_email
    safe_name = escape(full_name or "there")
    safe_url = escape(reset_url)
    message.set_content(
        f"Hi {full_name or 'there'},\n\n"
        "We received a request to reset your KaamConnect password. "
        "Open the link below to choose a new password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes. "
        "If you did not request a reset, you can safely ignore this email.\n\n"
        "KaamConnect"
    )
    message.add_alternative(
        f"<p>Hi {safe_name},</p>"
        "<p>We received a request to reset your KaamConnect password. "
        "Open the link below to choose a new password:</p>"
        f'<p><a href="{safe_url}">{safe_url}</a></p>'
        f"<p>This link expires in {settings.password_reset_expire_minutes} minutes. "
        "If you did not request a reset, you can safely ignore this email.</p>"
        "<p>KaamConnect</p>",
        subtype="html",
    )

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=15
            ) as smtp:
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=15
            ) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to send password reset email to %s", to_email)
        if not settings.is_production:
            logger.info("Password reset link for %s: %s", to_email, reset_url)
        return False
