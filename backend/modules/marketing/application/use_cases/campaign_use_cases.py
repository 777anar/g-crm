from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.marketing.application.dtos import (
    CreateCampaignInput,
    GetCampaignPerformanceInput,
    UpdateCampaignInput,
    UpdateCampaignStatusInput,
)
from modules.marketing.domain import events as marketing_events
from modules.marketing.domain.exceptions import CampaignImmutableError, InvalidCampaignTransitionError
from modules.marketing.domain.value_objects import (
    CAMPAIGN_STATUS_DRAFT,
    TERMINAL_CAMPAIGN_STATUSES,
    VALID_CAMPAIGN_CHANNELS,
    is_valid_campaign_transition,
)
from modules.marketing.infrastructure.models.campaign import Campaign
from modules.marketing.infrastructure.repositories.campaign_performance_repository import (
    CampaignPerformance,
    CampaignPerformanceRepository,
)
from modules.marketing.infrastructure.repositories.campaign_repository import CampaignRepository

MODULE = "marketing"


class CreateCampaignUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.campaigns = CampaignRepository(db)

    def execute(self, data: CreateCampaignInput) -> Campaign:
        if data.channel not in VALID_CAMPAIGN_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(VALID_CAMPAIGN_CHANNELS)}")

        campaign = Campaign(
            company_id=data.company_id,
            name=data.name,
            channel=data.channel,
            status=CAMPAIGN_STATUS_DRAFT,
            start_date=data.start_date,
            end_date=data.end_date,
            budget=data.budget,
            currency=data.currency,
            notes=data.notes,
            created_by=data.actor_user_id,
        )
        self.campaigns.add(campaign)

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="campaign.created",
            entity_type="campaign",
            entity_id=campaign.id,
            diff={"name": campaign.name, "channel": campaign.channel},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=marketing_events.CAMPAIGN_CREATED,
                company_id=data.company_id,
                payload={"campaign_id": str(campaign.id), "name": campaign.name, "channel": campaign.channel},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return campaign


class UpdateCampaignUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.campaigns = CampaignRepository(db)

    def execute(self, data: UpdateCampaignInput) -> Campaign:
        campaign = self.campaigns.get(company_id=data.company_id, campaign_id=data.campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
        if campaign.status in TERMINAL_CAMPAIGN_STATUSES:
            raise CampaignImmutableError(
                f"Campaign '{campaign.name}' can no longer be edited (status: {campaign.status})"
            )

        if data.name is not None:
            campaign.name = data.name
        if data.channel is not None:
            if data.channel not in VALID_CAMPAIGN_CHANNELS:
                raise ValueError(f"channel must be one of {sorted(VALID_CAMPAIGN_CHANNELS)}")
            campaign.channel = data.channel
        if data.start_date is not None:
            campaign.start_date = data.start_date
        if data.end_date is not None:
            campaign.end_date = data.end_date
        if data.budget is not None:
            campaign.budget = data.budget
        if data.notes is not None:
            campaign.notes = data.notes

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="campaign.updated",
            entity_type="campaign",
            entity_id=campaign.id,
            diff={"name": campaign.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=marketing_events.CAMPAIGN_UPDATED,
                company_id=data.company_id,
                payload={"campaign_id": str(campaign.id)},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return campaign


class UpdateCampaignStatusUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.campaigns = CampaignRepository(db)

    def execute(self, data: UpdateCampaignStatusInput) -> Campaign:
        campaign = self.campaigns.get(company_id=data.company_id, campaign_id=data.campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")

        if not is_valid_campaign_transition(current=campaign.status, target=data.status):
            raise InvalidCampaignTransitionError(
                f"Cannot move campaign from '{campaign.status}' to '{data.status}'"
            )

        old_status = campaign.status
        campaign.status = data.status

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE,
            actor_user_id=data.actor_user_id,
            action="campaign.status_changed",
            entity_type="campaign",
            entity_id=campaign.id,
            diff={"status": {"old": old_status, "new": campaign.status}},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=marketing_events.CAMPAIGN_STATUS_CHANGED,
                company_id=data.company_id,
                payload={"campaign_id": str(campaign.id), "old_status": old_status, "new_status": campaign.status},
                published_by_module=MODULE,
            ),
            self.db,
        )
        return campaign


class GetCampaignPerformanceUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.campaigns = CampaignRepository(db)
        self.performance = CampaignPerformanceRepository(db)

    def execute(self, data: GetCampaignPerformanceInput) -> CampaignPerformance:
        campaign = self.campaigns.get(company_id=data.company_id, campaign_id=data.campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
        return self.performance.get_performance(company_id=data.company_id, campaign_id=campaign.id)
