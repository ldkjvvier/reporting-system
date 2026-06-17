"""Email simulado: no envía nada real, registra el 'envío' en logs.

El adjunto ya queda persistido en disco (OUTBOX_DIR) por el builder, de modo que
puede inspeccionarse/descargarse aunque el envío sea simulado.
"""
import logging
import os
from typing import List

from app.integrations.email.base import EmailResult, EmailSender

logger = logging.getLogger("email.mock")


class MockEmailSender(EmailSender):
    def send(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: str,
        attachment_name: str,
    ) -> EmailResult:
        size = os.path.getsize(attachment_path) if os.path.exists(attachment_path) else 0
        logger.info(
            "[MOCK EMAIL] para=%s | asunto=%s | adjunto=%s (%d bytes)",
            ", ".join(recipients), subject, attachment_name, size,
        )
        return EmailResult(
            status="mock_sent",
            detail=f"Simulado a {len(recipients)} destinatario(s); adjunto {attachment_name}",
        )
