"""Task Intelligence: company-wide (not tied to one entity) suggestions for
new tasks/reminders, an assignee suggestion based on current open-task
workload, and overdue-risk detection for tasks due soon.

Reads CRM's Task/Lead and Communication's Conversation models directly;
never writes to them -- see AIRecommendation's docstring on why accepting a
task_suggestion still requires the human to actually create the task
through the existing Tasks screen (this module never calls
CreateTaskUseCase itself).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.audit.service import record_audit
from core.auth.models import UserCompanyRole
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import SuggestTasksInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import (
    ANALYSIS_KIND_TASK,
    RECOMMENDATION_TYPE_ASSIGNEE_SUGGESTION,
    RECOMMENDATION_TYPE_OVERDUE_RISK,
    RECOMMENDATION_TYPE_REMINDER_SUGGESTION,
    RECOMMENDATION_TYPE_TASK_SUGGESTION,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.communication.infrastructure.models.conversation import Conversation
from modules.crm.domain.value_objects import LEAD_STATUS_CONTACTED, LEAD_STATUS_NEW
from modules.crm.infrastructure.models.lead import Lead
from modules.crm.infrastructure.models.task import Task
from modules.crm.domain.value_objects import TERMINAL_TASK_STATUSES

MODULE_NAME = "ai"
_STALE_LEAD_AFTER_HOURS = 48
_OVERDUE_RISK_WINDOW_HOURS = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    return uuid.UUID(value) if value else None


class SuggestTasksUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: SuggestTasksInput) -> List[AIRecommendation]:
        stale_cutoff = _now() - timedelta(hours=_STALE_LEAD_AFTER_HOURS)
        stale_leads = list(self.db.scalars(
            select(Lead).where(
                Lead.company_id == data.company_id,
                Lead.status.in_((LEAD_STATUS_NEW, LEAD_STATUS_CONTACTED)),
                Lead.created_at <= stale_cutoff,
            ).limit(50)
        ).all())

        stale_conversations = list(self.db.scalars(
            select(Conversation).where(
                Conversation.company_id == data.company_id,
                Conversation.status == "open",
                Conversation.unread_count > 0,
            ).limit(50)
        ).all())

        workload_rows = self.db.execute(
            select(Task.assigned_to, func.count(Task.id))
            .where(
                Task.company_id == data.company_id,
                Task.assigned_to.isnot(None),
                Task.status.notin_(TERMINAL_TASK_STATUSES),
            )
            .group_by(Task.assigned_to)
        ).all()
        workload = {str(user_id): count for user_id, count in workload_rows}

        # Every company member with zero open tasks doesn't show up in the
        # GROUP BY above -- add them at 0 so they're a valid (and likely
        # preferred) assignee candidate, not silently excluded.
        member_ids = list(self.db.scalars(
            select(UserCompanyRole.user_id).where(UserCompanyRole.company_id == data.company_id)
        ).all())
        for member_id in member_ids:
            workload.setdefault(str(member_id), 0)

        risk_cutoff = _now() + timedelta(hours=_OVERDUE_RISK_WINDOW_HOURS)
        at_risk_tasks = list(self.db.scalars(
            select(Task).where(
                Task.company_id == data.company_id,
                Task.status.notin_(TERMINAL_TASK_STATUSES),
                Task.due_date.isnot(None),
                Task.due_date <= risk_cutoff,
            ).limit(50)
        ).all())

        context = {
            "stale_leads": [{"id": str(l.id), "full_name": l.full_name} for l in stale_leads],
            "stale_conversations": [
                {"id": str(c.id), "external_contact_id": c.external_contact_id, "external_contact_name": c.external_contact_name}
                for c in stale_conversations
            ],
            "user_workload": workload,
            "at_risk_tasks": [{"id": str(t.id), "title": t.title} for t in at_risk_tasks],
        }
        prompt = (
            "Suggest CRM follow-up tasks for a stone/slab gallery business.\n"
            f"Stale leads (no contact in {_STALE_LEAD_AFTER_HOURS}h+): {len(stale_leads)}\n"
            f"Unanswered open conversations: {len(stale_conversations)}\n"
            f"Team open-task workload: {workload}\n"
            f"Tasks due within {_OVERDUE_RISK_WINDOW_HOURS}h: {len(at_risk_tasks)}\n"
            "Suggest new tasks and reminders, an assignee based on lowest current workload, and flag "
            "overdue risks."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(
            provider.suggest_tasks,
            prompt=prompt,
            context=context,
            db=self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_TASK,
            provider=provider,
        )
        d = timed.result.data

        builder = RecommendationBuilder(
            self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_TASK,
            related_entity_type=None,
            related_entity_id=None,
            provider=provider,
            prompt=prompt,
            confidence=timed.result.confidence,
            execution_time_ms=timed.execution_time_ms,
            provider_call_id=timed.provider_call_id,
        )

        for task in d["tasks"]:
            builder.add(
                RECOMMENDATION_TYPE_TASK_SUGGESTION,
                task,
                task["title"],
                related_entity_type=task.get("related_entity_type"),
                related_entity_id=_as_uuid(task.get("related_entity_id")),
            )
        for reminder in d["reminders"]:
            builder.add(
                RECOMMENDATION_TYPE_REMINDER_SUGGESTION,
                reminder,
                reminder["title"],
                related_entity_type=reminder.get("related_entity_type"),
                related_entity_id=_as_uuid(reminder.get("related_entity_id")),
            )
        if d["assignee_suggestion"]:
            builder.add(
                RECOMMENDATION_TYPE_ASSIGNEE_SUGGESTION,
                {"assignee_suggestion": d["assignee_suggestion"], "workload": workload},
                "Lowest-workload assignee suggested for new tasks",
            )
        for risk in d["overdue_risks"]:
            builder.add(
                RECOMMENDATION_TYPE_OVERDUE_RISK,
                risk,
                f"At risk of going overdue: {risk.get('title')}",
                related_entity_type="task",
                related_entity_id=_as_uuid(risk.get("task_id")),
            )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.tasks_suggested",
            entity_type="company",
            entity_id=data.company_id,
            diff={"recommendation_count": len(builder.created), "provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.TASKS_SUGGESTED,
                company_id=data.company_id,
                payload={"recommendation_count": len(builder.created)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
