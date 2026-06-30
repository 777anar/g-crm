"""Opaque cursor encode/decode for the offset-based cursor pagination
documented in API_SPECIFICATION.md section 4 (`{items, next_cursor}`).

Cursors are a base64-encoded `{"offset": N}` JSON object -- offset-based
under the hood, but opaque to clients per the documented contract, so the
encoding can change later (e.g. to a real keyset cursor) without breaking
callers who only ever pass the cursor back verbatim.
"""
import base64
import json
from typing import Optional


def encode_cursor(*, offset: int) -> str:
    payload = json.dumps({"offset": offset}).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_cursor(cursor: Optional[str]) -> int:
    """Returns the offset encoded in `cursor`, or 0 if `cursor` is None or
    malformed (fails open to "start from the beginning" rather than erroring,
    since a stale/tampered cursor shouldn't be able to break the list view)."""
    if not cursor:
        return 0
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        offset = int(payload.get("offset", 0))
        return offset if offset >= 0 else 0
    except Exception:
        return 0
