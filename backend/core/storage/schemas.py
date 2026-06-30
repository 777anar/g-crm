import uuid

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    storage_path: str
    mime_type: str


class SignedUrlOut(BaseModel):
    url: str
