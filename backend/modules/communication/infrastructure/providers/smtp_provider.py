"""Real outbound email via SMTP (smtplib/email, Python stdlib -- no extra
dependency). IMAP inbound sync lives in imap_sync_client.py since receiving
mail is fundamentally a pull operation, not something that fits
ChannelProvider.send()'s push shape; both share the same ChannelCredential
config blob for one `email` channel.

Outbound media: same convention as the Meta providers -- for message_type in
{image, document, audio, video}, `body` is the URL of an already-uploaded
file (core Documents pipeline), fetched here and attached as a real email
attachment, since email attachments are meaningfully different from a
"send a link" media message.
"""
import smtplib
import uuid
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any, Dict

import httpx

from modules.communication.domain.exceptions import ProviderConfigurationError, ProviderRequestError
from modules.communication.infrastructure.providers.base import ChannelProvider

REQUIRED_CONFIG_FIELDS = ("smtp_host", "smtp_port", "smtp_username", "smtp_password", "from_address")
_MEDIA_TYPES = {"image", "document", "audio", "video"}


class SMTPEmailProvider(ChannelProvider):
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"SMTP config missing required field(s): {', '.join(missing)}")
        self.config = config

    def _connect(self) -> smtplib.SMTP:
        host = self.config["smtp_host"]
        port = int(self.config["smtp_port"])
        encryption = (self.config.get("smtp_encryption") or "starttls").lower()
        timeout = 15
        if encryption == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            if encryption == "starttls":
                server.starttls()
        server.login(self.config["smtp_username"], self.config["smtp_password"])
        return server

    def _fetch_media(self, url: str) -> bytes:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url)
        if response.status_code >= 400:
            raise ProviderRequestError(f"Could not fetch attachment from {url}: {response.status_code}")
        return response.content

    def send(self, *, channel, external_contact_id: str, body: str, message_type: str) -> str:
        message = EmailMessage()
        message["From"] = self.config["from_address"]
        message["To"] = external_contact_id
        message["Subject"] = self.config.get("default_subject") or f"Message from {getattr(channel, 'display_name', 'G-STONE')}"
        message_id = make_msgid()
        message["Message-ID"] = message_id

        if message_type in _MEDIA_TYPES:
            message.set_content(f"See the attached file: {body}")
            content = self._fetch_media(body)
            filename = body.rsplit("/", 1)[-1] or "attachment"
            maintype = {"image": "image", "audio": "audio", "video": "video", "document": "application"}[message_type]
            message.add_attachment(content, maintype=maintype, subtype="octet-stream", filename=filename)
        else:
            message.set_content(body)

        server = self._connect()
        try:
            server.send_message(message)
        finally:
            server.quit()
        return message_id.strip("<>") or f"smtp-{uuid.uuid4()}"

    def test_connection(self) -> Dict[str, Any]:
        server = self._connect()
        server.quit()
        return {"ok": True, "detail": f"Connected to {self.config['smtp_host']}:{self.config['smtp_port']}"}
