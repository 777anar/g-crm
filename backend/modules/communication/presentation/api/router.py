from fastapi import APIRouter

from modules.communication.presentation.api.channels import router as channels_router
from modules.communication.presentation.api.conversations import router as conversations_router
from modules.communication.presentation.api.inbound import router as inbound_router
from modules.communication.presentation.api.integrations import router as integrations_router
from modules.communication.presentation.api.templates import router as templates_router
from modules.communication.presentation.api.webhooks import router as webhooks_router

communication_router = APIRouter()
communication_router.include_router(channels_router)
communication_router.include_router(conversations_router)
communication_router.include_router(templates_router)
communication_router.include_router(inbound_router)
communication_router.include_router(integrations_router)
communication_router.include_router(webhooks_router)
