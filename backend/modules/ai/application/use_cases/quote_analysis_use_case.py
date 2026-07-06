"""Sales Intelligence: the AI Quote Assistant. Analyzes one Quote against
this company's own historical accepted quotes and produces product/cross-
sell/upsell recommendations, a discount suggestion, margin-risk and price-
anomaly detection, and a delivery-complexity estimate.

All "historical" signal comes from this company's own past QuoteSectionItem
rows (bounded, pragmatic Python aggregation -- the same approach Reports
uses at this dataset scale, not a materialized analytics table). Reads
Sales/Catalog models directly; never writes to them.
"""
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.errors import NotFoundError
from core.audit.service import record_audit
from core.events.event_bus import event_bus
from core.events.event_envelope import Event
from modules.ai.application.dtos import AnalyzeQuoteInput
from modules.ai.application.use_cases._shared import RecommendationBuilder, run_provider
from modules.ai.domain import events as ai_events
from modules.ai.domain.value_objects import (
    ANALYSIS_KIND_QUOTE,
    RECOMMENDATION_TYPE_CROSS_SELL,
    RECOMMENDATION_TYPE_DELIVERY_COMPLEXITY,
    RECOMMENDATION_TYPE_DISCOUNT_RECOMMENDATION,
    RECOMMENDATION_TYPE_MARGIN_RISK,
    RECOMMENDATION_TYPE_PRICE_ANOMALY,
    RECOMMENDATION_TYPE_PRODUCT_RECOMMENDATION,
    RECOMMENDATION_TYPE_UPSELL,
)
from modules.ai.infrastructure.models.recommendation import AIRecommendation
from modules.ai.infrastructure.providers.registry import get_provider
from modules.catalog.infrastructure.models.material import StoneMaterial
from modules.sales.domain.value_objects import QUOTE_STATUS_ACCEPTED
from modules.sales.infrastructure.models.quote import Quote
from modules.sales.infrastructure.models.quote_section import QuoteSection
from modules.sales.infrastructure.models.quote_section_item import QuoteSectionItem

MODULE_NAME = "ai"


def _material_summary(material_id: UUID, materials_by_id: dict, material_prices: dict, count: Optional[int] = None) -> dict:
    material = materials_by_id.get(material_id)
    prices = material_prices.get(material_id) or []
    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    return {
        "material_id": str(material_id),
        "material_name": material.name if material else "Unknown material",
        "count": count,
        "avg_sale_price": avg_price,
    }


class AnalyzeQuoteUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, data: AnalyzeQuoteInput) -> List[AIRecommendation]:
        quote = self.db.scalar(select(Quote).where(Quote.id == data.quote_id, Quote.company_id == data.company_id))
        if quote is None:
            raise NotFoundError("Quote not found")

        items = list(self.db.scalars(
            select(QuoteSectionItem).where(
                QuoteSectionItem.company_id == data.company_id, QuoteSectionItem.quote_id == quote.id
            )
        ).all())
        sections = list(self.db.scalars(
            select(QuoteSection).where(
                QuoteSection.company_id == data.company_id, QuoteSection.quote_id == quote.id
            )
        ).all())
        total_area_m2 = float(sum((s.total_measured_area or 0) for s in sections))

        accepted_quote_ids = list(self.db.scalars(
            select(Quote.id).where(
                Quote.company_id == data.company_id, Quote.status == QUOTE_STATUS_ACCEPTED, Quote.id != quote.id
            ).limit(500)
        ).all())

        historical_items: List[QuoteSectionItem] = []
        if accepted_quote_ids:
            historical_items = list(self.db.scalars(
                select(QuoteSectionItem).where(
                    QuoteSectionItem.company_id == data.company_id,
                    QuoteSectionItem.quote_id.in_(accepted_quote_ids),
                )
            ).all())

        material_counts: Dict[UUID, int] = {}
        material_prices: Dict[UUID, List[float]] = {}
        quote_material_map: Dict[UUID, set] = {}
        for item in historical_items:
            if not item.material_id:
                continue
            material_counts[item.material_id] = material_counts.get(item.material_id, 0) + 1
            material_prices.setdefault(item.material_id, []).append(float(item.unit_sale_price))
            quote_material_map.setdefault(item.quote_id, set()).add(item.material_id)

        current_material_ids = {i.material_id for i in items if i.material_id}
        co_occurrence_counts: Dict[UUID, int] = {}
        for materials_in_quote in quote_material_map.values():
            if materials_in_quote & current_material_ids:
                for material_id in materials_in_quote - current_material_ids:
                    co_occurrence_counts[material_id] = co_occurrence_counts.get(material_id, 0) + 1

        material_ids_needed = set(material_counts) | set(co_occurrence_counts) | current_material_ids
        materials_by_id = {}
        if material_ids_needed:
            rows = list(self.db.scalars(
                select(StoneMaterial).where(
                    StoneMaterial.company_id == data.company_id, StoneMaterial.id.in_(material_ids_needed)
                )
            ).all())
            materials_by_id = {m.id: m for m in rows}

        top_materials = [
            _material_summary(mid, materials_by_id, material_prices, count)
            for mid, count in sorted(material_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        ]
        co_occurring_materials = [
            _material_summary(mid, materials_by_id, material_prices, count)
            for mid, count in sorted(co_occurrence_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        ]

        # Upsell: same material_type as something already in this quote, but
        # with a meaningfully higher historical average sale price -- a real
        # comparison against this company's own transaction history, not a
        # static price-list lookup.
        current_types = {
            materials_by_id[mid].material_type
            for mid in current_material_ids
            if mid in materials_by_id and materials_by_id[mid].material_type
        }
        upsell_candidates = []
        for material_id, prices in material_prices.items():
            material = materials_by_id.get(material_id)
            if not material or material.material_type not in current_types or material_id in current_material_ids:
                continue
            avg_price = sum(prices) / len(prices)
            matching_current = [
                i for i in items
                if i.material_id and materials_by_id.get(i.material_id)
                and materials_by_id[i.material_id].material_type == material.material_type
            ]
            if not matching_current:
                continue
            current_avg = sum(float(i.unit_sale_price) for i in matching_current) / len(matching_current)
            if current_avg and avg_price > current_avg * 1.15:
                upsell_candidates.append(_material_summary(material_id, materials_by_id, material_prices))
        upsell_candidates.sort(key=lambda m: m["avg_sale_price"] or 0, reverse=True)

        accepted_quotes = []
        if accepted_quote_ids:
            accepted_quotes = list(self.db.scalars(select(Quote).where(Quote.id.in_(accepted_quote_ids))).all())
        discount_pcts = [
            float(q.discount_amount) / float(q.subtotal_gross) * 100
            for q in accepted_quotes
            if q.subtotal_gross and float(q.subtotal_gross) > 0
        ]
        avg_discount_pct = sum(discount_pcts) / len(discount_pcts) if discount_pcts else 0.0

        material_price_stats = {
            str(mid): {"avg_sale_price": sum(prices) / len(prices)} for mid, prices in material_prices.items()
        }

        context = {
            "items": [
                {
                    "id": str(item.id),
                    "description": item.description,
                    "material_id": str(item.material_id) if item.material_id else None,
                    "unit_sale_price": str(item.unit_sale_price),
                    "unit_cost_price": str(item.unit_cost_price),
                }
                for item in items
            ],
            "top_materials": top_materials,
            "co_occurring_materials": co_occurring_materials,
            "upsell_candidates": upsell_candidates,
            "avg_discount_pct": avg_discount_pct,
            "material_price_stats": material_price_stats,
            "section_item_count": len(items),
            "total_area_m2": total_area_m2,
        }
        prompt = (
            f"Analyze quote {quote.quote_number} for a stone/slab gallery business: {len(items)} line item(s), "
            f"{total_area_m2:.1f} m2 total. Recommend additional products, cross-sell and upsell options based on "
            f"this company's own accepted-quote history, suggest a discount, flag margin risk or price anomalies "
            f"per line, and estimate delivery complexity."
        )

        provider = get_provider(data.provider_name)
        timed = run_provider(provider.analyze_quote, prompt=prompt, context=context)
        d = timed.result.data

        builder = RecommendationBuilder(
            self.db,
            company_id=data.company_id,
            actor_user_id=data.actor_user_id,
            analysis_kind=ANALYSIS_KIND_QUOTE,
            related_entity_type="quote",
            related_entity_id=quote.id,
            provider=provider,
            prompt=prompt,
            confidence=timed.result.confidence,
            execution_time_ms=timed.execution_time_ms,
        )
        if d["product_recommendations"]:
            builder.add(
                RECOMMENDATION_TYPE_PRODUCT_RECOMMENDATION,
                {"products": d["product_recommendations"]},
                f"{len(d['product_recommendations'])} product recommendation(s)",
            )
        if d["cross_sell_suggestions"]:
            builder.add(
                RECOMMENDATION_TYPE_CROSS_SELL,
                {"products": d["cross_sell_suggestions"]},
                f"{len(d['cross_sell_suggestions'])} cross-sell suggestion(s)",
            )
        if d["upsell_suggestions"]:
            builder.add(
                RECOMMENDATION_TYPE_UPSELL,
                {"products": d["upsell_suggestions"]},
                f"{len(d['upsell_suggestions'])} upsell suggestion(s)",
            )
        builder.add(
            RECOMMENDATION_TYPE_DISCOUNT_RECOMMENDATION,
            d["discount_recommendation"],
            f"Suggested discount: {d['discount_recommendation']['suggested_pct']}%",
        )
        if d["margin_risks"]:
            builder.add(
                RECOMMENDATION_TYPE_MARGIN_RISK,
                {"risks": d["margin_risks"]},
                f"{len(d['margin_risks'])} line item(s) with thin margin",
            )
        if d["price_anomalies"]:
            builder.add(
                RECOMMENDATION_TYPE_PRICE_ANOMALY,
                {"anomalies": d["price_anomalies"]},
                f"{len(d['price_anomalies'])} price anomaly(ies) detected",
            )
        builder.add(
            RECOMMENDATION_TYPE_DELIVERY_COMPLEXITY,
            {"complexity": d["delivery_complexity"]},
            f"Delivery complexity: {d['delivery_complexity']}",
        )

        record_audit(
            self.db,
            company_id=data.company_id,
            module=MODULE_NAME,
            actor_user_id=data.actor_user_id,
            action="ai.quote_analyzed",
            entity_type="quote",
            entity_id=quote.id,
            diff={"recommendation_count": len(builder.created), "provider": provider.name},
        )
        self.db.flush()

        event_bus.publish(
            Event(
                name=ai_events.QUOTE_ANALYZED,
                company_id=data.company_id,
                payload={"quote_id": str(quote.id), "recommendation_count": len(builder.created)},
                published_by_module=MODULE_NAME,
            ),
            self.db,
        )
        return builder.created
