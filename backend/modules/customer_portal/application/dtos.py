import uuid
from dataclasses import dataclass


@dataclass
class ActorContext:
    company_id: uuid.UUID
    actor_user_id: uuid.UUID


@dataclass
class EnablePortalAccessInput(ActorContext):
    customer_id: uuid.UUID
    email: str
    password: str


@dataclass
class ResetPortalPasswordInput(ActorContext):
    customer_id: uuid.UUID
    password: str


@dataclass
class SetPortalAccessActiveInput(ActorContext):
    customer_id: uuid.UUID
    is_active: bool
