import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.communication.infrastructure.models.channel import Channel


class ChannelRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, channel: Channel) -> Channel:
        self.db.add(channel)
        self.db.flush()
        return channel

    def get(self, *, company_id: uuid.UUID, channel_id: uuid.UUID) -> Optional[Channel]:
        return self.db.scalar(
            select(Channel).where(Channel.id == channel_id, Channel.company_id == company_id)
        )

    def get_by_id_any_company(self, channel_id: uuid.UUID) -> Optional[Channel]:
        """Unscoped by company -- used only by public webhook receivers,
        which have no authenticated active-company context and must resolve
        company_id *from* the channel, not the other way around. Every
        other caller in this codebase goes through `get()` instead."""
        return self.db.scalar(select(Channel).where(Channel.id == channel_id))

    def list(
        self,
        *,
        company_id: uuid.UUID,
        channel_type: Optional[str] = None,
        include_inactive: bool = True,
    ) -> List[Channel]:
        stmt = select(Channel).where(Channel.company_id == company_id)
        if channel_type:
            stmt = stmt.where(Channel.channel_type == channel_type)
        if not include_inactive:
            stmt = stmt.where(Channel.is_active.is_(True))
        stmt = stmt.order_by(Channel.created_at.asc())
        return list(self.db.scalars(stmt).all())
