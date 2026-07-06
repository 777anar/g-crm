"""IMAP inbound mail sync. Not a ChannelProvider -- receiving mail is
fundamentally a pull operation (there's no "inbound webhook" for raw IMAP),
so this is a plain helper `SyncImapMailboxUseCase` (application layer) calls
directly, mirroring exactly how Tasks & Reminders' reminder/overdue checks
are a pull endpoint rather than a scheduled push, since this codebase has no
background job scheduler.
"""
import email
import imaplib
from dataclasses import dataclass, field
from email.header import decode_header
from email.message import Message as EmailMessage
from email.utils import parseaddr
from typing import Any, Dict, List, Optional

from modules.communication.domain.exceptions import ProviderConfigurationError

REQUIRED_CONFIG_FIELDS = ("imap_host", "imap_port", "imap_username", "imap_password")


@dataclass
class FetchedAttachment:
    filename: str
    content: bytes
    mime_type: str


@dataclass
class FetchedEmail:
    uid: int
    from_address: str
    from_name: Optional[str]
    subject: str
    body: str
    attachments: List[FetchedAttachment] = field(default_factory=list)


def _decode_header_value(raw: Optional[str]) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _extract_body_and_attachments(msg: EmailMessage) -> tuple[str, List[FetchedAttachment]]:
    body = ""
    attachments: List[FetchedAttachment] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition") or "")
            content_type = part.get_content_type()
            if "attachment" in content_disposition or (part.get_filename() and content_type != "text/plain"):
                filename = _decode_header_value(part.get_filename()) or "attachment"
                payload = part.get_payload(decode=True)
                if payload:
                    attachments.append(FetchedAttachment(filename=filename, content=payload, mime_type=content_type))
            elif content_type == "text/plain" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

    return body, attachments


class ImapMailboxClient:
    def __init__(self, config: Dict[str, Any]):
        missing = [f for f in REQUIRED_CONFIG_FIELDS if not config.get(f)]
        if missing:
            raise ProviderConfigurationError(f"IMAP config missing required field(s): {', '.join(missing)}")
        self.config = config

    def _connect(self) -> imaplib.IMAP4:
        host = self.config["imap_host"]
        port = int(self.config["imap_port"])
        if self.config.get("imap_use_ssl", True):
            conn = imaplib.IMAP4_SSL(host, port, timeout=20)
        else:
            conn = imaplib.IMAP4(host, port, timeout=20)
        conn.login(self.config["imap_username"], self.config["imap_password"])
        conn.select(self.config.get("imap_folder", "INBOX"))
        return conn

    def test_connection(self) -> Dict[str, Any]:
        conn = self._connect()
        try:
            return {"ok": True, "detail": f"Connected to {self.config['imap_host']} ({self.config.get('imap_folder', 'INBOX')})"}
        finally:
            conn.logout()

    def fetch_new_messages(self, *, since_uid: Optional[int]) -> List[FetchedEmail]:
        """Returns every message with a UID greater than `since_uid`
        (or every message on the first sync, when since_uid is None)."""
        conn = self._connect()
        try:
            criteria = "ALL" if since_uid is None else f"UID {since_uid + 1}:*"
            status, data = conn.uid("search", None, criteria)
            if status != "OK" or not data or not data[0]:
                return []
            uids = [int(uid) for uid in data[0].split()]
            if since_uid is not None:
                uids = [uid for uid in uids if uid > since_uid]

            results: List[FetchedEmail] = []
            for uid in uids:
                status, msg_data = conn.uid("fetch", str(uid), "(RFC822)")
                if status != "OK" or not msg_data or msg_data[0] is None:
                    continue
                raw = msg_data[0][1]
                parsed = email.message_from_bytes(raw)
                from_name, from_address = parseaddr(_decode_header_value(parsed.get("From")))
                subject = _decode_header_value(parsed.get("Subject"))
                body, attachments = _extract_body_and_attachments(parsed)
                results.append(
                    FetchedEmail(
                        uid=uid,
                        from_address=from_address,
                        from_name=from_name or None,
                        subject=subject,
                        body=body,
                        attachments=attachments,
                    )
                )
            return results
        finally:
            conn.logout()
