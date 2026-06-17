"""Envío real de correo vía Microsoft Graph (Azure) con autenticación client_credentials.

Se activa cuando EMAIL_MODE=real y existen las credenciales de Azure.
Implementación lista para usar; no se ejercita hasta cargar credenciales reales.
"""
import base64
import os
from typing import List

import httpx

from app.config import settings
from app.integrations.email.base import EmailResult, EmailSender

GRAPH_SCOPE = "https://graph.microsoft.com/.default"


class GraphEmailSender(EmailSender):
    def _get_token(self) -> str:
        url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": settings.AZURE_CLIENT_ID,
            "client_secret": settings.AZURE_CLIENT_SECRET,
            "scope": GRAPH_SCOPE,
            "grant_type": "client_credentials",
        }
        resp = httpx.post(url, data=data, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def send(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: str,
        attachment_name: str,
    ) -> EmailResult:
        try:
            token = self._get_token()
            with open(attachment_path, "rb") as fh:
                content_b64 = base64.b64encode(fh.read()).decode("utf-8")

            message = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "Text", "content": body},
                    "toRecipients": [
                        {"emailAddress": {"address": addr}} for addr in recipients
                    ],
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": attachment_name,
                            "contentBytes": content_b64,
                        }
                    ],
                },
                "saveToSentItems": True,
            }
            sender = settings.MAIL_SENDER
            url = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=message,
                timeout=60,
            )
            resp.raise_for_status()
            return EmailResult(status="sent", detail=f"Enviado a {len(recipients)} destinatario(s)")
        except Exception as exc:  # noqa: BLE001
            return EmailResult(status="failed", detail=str(exc))
