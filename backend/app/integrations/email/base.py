"""Interfaz común para el envío de correo con adjuntos."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class EmailResult:
    status: str        # "mock_sent" | "sent" | "failed"
    detail: str = ""


class EmailSender(ABC):
    @abstractmethod
    def send(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: str,
        attachment_name: str,
    ) -> EmailResult:
        ...
