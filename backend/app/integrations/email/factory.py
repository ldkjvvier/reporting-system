"""Selecciona la implementación de EmailSender según configuración."""
from app.config import settings
from app.integrations.email.base import EmailSender


def get_email_sender() -> EmailSender:
    use_real = (
        settings.EMAIL_MODE == "real"
        and settings.AZURE_TENANT_ID
        and settings.AZURE_CLIENT_ID
        and settings.AZURE_CLIENT_SECRET
        and settings.MAIL_SENDER
    )
    if use_real:
        from app.integrations.email.real import GraphEmailSender

        return GraphEmailSender()
    from app.integrations.email.mock import MockEmailSender

    return MockEmailSender()
