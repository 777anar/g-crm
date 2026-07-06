import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.channel_credential import ChannelCredential


class ChannelCredentialRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, credential: ChannelCredential) -> ChannelCredential:
        self.db.add(credential)
        self.db.flush()
        return credential

    def get_by_channel(self, *, company_id: uuid.UUID, channel_id: uuid.UUID) -> Optional[ChannelCredential]:
        return self.db.scalar(
            select(ChannelCredential).where(
                ChannelCredential.channel_id == channel_id, ChannelCredential.company_id == company_id
            )
        )

    def delete(self, credential: ChannelCredential) -> None:
        self.db.delete(credential)
        self.db.flush()
