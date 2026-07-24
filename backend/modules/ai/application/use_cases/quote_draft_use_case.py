"""AI draft generation (Phase 21 follow-through): suggested Quote line-item
descriptions for one Project's already-specified Rooms/Items, created as a
single `quote_draft_line_items` recommendation. Draft-only -- a human uses
these drafts as a starting point when building the actual Quote through
Sales' existing quote-creation screens; this use case never creates a Quote
or QuoteSectionItem itself.

Exact quantities/prices are computed deterministically from real
ProjectItem/PriceListEntry data, never approximated by the model: the
provider only supplies a line description and a bounded (0-20%) waste-factor
suggestion, applied to the real measured quantity in code.
"""
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import DraftQuoteLineItemsInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import ANALYSIS_KIND_QUOTE, RECOMMENDATION_TYPE_QUOTE_DRAFT_LINE_ITEMS
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.catalog.infrastructure.repositories.price_list_repository import (
    PriceListEntryRepository,
    PriceListRepository,
)
from modules.sales.infrastructure.models.project import Project
from modules.sales.infrastructure.repositories.project_item_repository import ProjectItemRepository
from modules.sales.infrastructure.repositories.room_repository import RoomRepository

MODULE_NAME = "ai"


class DraftQuoteLineItemsUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: DraftQuoteLineItemsInput) -> List[AIRecommendation]:
        project = self.db.scalar(
            select(Project).where(Project.id == data.project_id, Project.company_id == data.company_id)
        )
        if project is None:
            raise NotFoundError("Project not found")

        rooms = RoomRepository(self.db).list_for_project(company_id=data.company_id, project_id=project.id)
        room_names = {r.id: r.name for r in rooms}
        items = ProjectItemRepository(self.db).list_for_project(company_id=data.company_id, project_id=project.id)

        material_ids = {i.material_id for i in items if i.material_id}
        materials_by_id: Dict[str, StoneMaterial] = {}
        if material_ids:
            rows = list(self.db.scalars(
                select(StoneMaterial).where(
                    StoneMaterial.company_id == data.company_id, StoneMaterial.id.in_(material_ids)
                )
            ).all())
            materials_by_id = {m.id: m for m in rows}

        default_price_list = next(
            (pl for pl in PriceListRepository(self.db).list(company_id=data.company_id) if pl.is_default), None
        )
        price_entry_repo = PriceListEntryRepository(self.db)

        context_items = []
        for item in items:
            material = materials_by_id.get(item.material_id) if item.material_id else None
            unit_sale_price: Optional[Decimal] = None
            if material and default_price_list:
                entry = price_entry_repo.get_for_material(
                    company_id=data.company_id, price_list_id=default_price_list.id, material_id=material.id
                )
                if entry:
                    unit_sale_price = entry.sale_price
            context_items.append({
                "project_item_id": str(item.id),
                "room_name": room_names.get(item.room_id),
                "item_name": item.name,
                "material_id": str(material.id) if material else None,
                "material_name": material.name if material else None,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "notes": item.notes,
                "unit_sale_price": str(unit_sale_price) if unit_sale_price is not None else None,
            })

        context = {
            "project": {"id": str(project.id), "name": project.name, "project_type": project.project_type},
            "items": context_items,
        }
        prompt = (
            f"Draft Quote line-item suggestions for project '{project.name}' ({len(context_items)} item(s) across "
            f"{len(rooms)} room(s)) for a stone/slab gallery business. For each item, write a clear customer-facing "
            "line description (room + material) and suggest a cutting/offcut waste-factor percentage (0-20) if "
            "one is warranted for that item's unit of measure."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(
            provider.draft_quote_line_items,
            prompt=prompt,
            context=context,
            db=self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_QUOTE,
            provider=provider,
        )
        drafted_by_id = {d["project_item_id"]: d for d in timed.result.data["items"]}

        response_items = []
        for ctx_item in context_items:
            draft = drafted_by_id.get(ctx_item["project_item_id"])
            if not draft:
                continue
            base_quantity = Decimal(ctx_item["quantity"])
            waste_factor_pct = Decimal(str(draft["waste_factor_pct"]))
            suggested_quantity = (base_quantity * (1 + waste_factor_pct / 100)).quantize(Decimal("0.001"))
            unit_sale_price = Decimal(ctx_item["unit_sale_price"]) if ctx_item["unit_sale_price"] is not None else None
            estimated_total = (
                (suggested_quantity * unit_sale_price).quantize(Decimal("0.01"))
                if unit_sale_price is not None else None
            )
            response_items.append({
                "project_item_id": ctx_item["project_item_id"],
                "room_name": ctx_item["room_name"],
                "item_name": ctx_item["item_name"],
                "material_id": ctx_item["material_id"],
                "material_name": ctx_item["material_name"],
                "description": draft["description"],
                "unit": ctx_item["unit"],
                "base_quantity": ctx_item["quantity"],
                "waste_factor_pct": str(waste_factor_pct),
                "suggested_quantity": str(suggested_quantity),
                "unit_sale_price": str(unit_sale_price) if unit_sale_price is not None else None,
                "estimated_total": str(estimated_total) if estimated_total is not None else None,
            })

        builder = RecommendationBuilder(
            self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_QUOTE,
            related_entity_type="project",
            related_entity_id=project.id,
            provider=provider,
            prompt=prompt,
            confidence=timed.result.confidence,
            execution_time_ms=timed.execution_time_ms,
            provider_call_id=timed.provider_call_id,
        )
        builder.add(
            RECOMMENDATION_TYPE_QUOTE_DRAFT_LINE_ITEMS,
            {"items": response_items},
            f"{len(response_items)} draft quote line item(s) suggested",
        )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.quote_line_items_drafted",
            entity_type="project",
            entity_id=project.id,
            diff={"provider": provider.name, "item_count": len(response_items)},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.QUOTE_LINE_ITEMS_DRAFTED,
                company_id=data.company_id,
                payload={"project_id": str(project.id), "item_count": len(response_items)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
