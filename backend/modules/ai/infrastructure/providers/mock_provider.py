"""The only provider registered today (see registry.py). Per this module's
explicit scope, it does not call out to OpenAI/Anthropic/Gemini/Ollama/Azure
OpenAI -- it computes a real, deterministic heuristic analysis from the
structured `context` a use case builds (not from parsing the `prompt` text,
which is stored purely for audit/what-would-have-been-sent-to-a-real-LLM
purposes -- see AIProvider's docstring). Every heuristic below is a genuine,
inspectable rule over real data, not a random placeholder, so the module is
actually useful standalone and the swap to a real provider later changes
only which class answers these same four questions.
"""
import re
from typing import Any, Dict, List, Optional

from modules.ai.infrastructure.providers.base import AIAnalysisResult, AIProvider

_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3}[\s-]?\d{2,4}[\s-]?\d{0,4}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_COMPANY_SUFFIX_RE = re.compile(r"\b([A-Z][\w&.]*(?:\s+[A-Z][\w&.]*){0,3}\s+(?:MMC|LLC|Ltd\.?|Inc\.?|Co\.?))\b")
_ADDRESS_HINT_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9əöüğşçıİĞÖÜŞÇ.'\-]+\s+(?:str\.?|street|küç\.?|ave\.?|avenue|road|rd\.?)\b",
    re.IGNORECASE,
)

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_AZERBAIJANI_CHARS = set("əöüğşçıİĞÖÜŞÇıə")

_NEGATIVE_WORDS = {"problem", "issue", "bad", "angry", "complaint", "refund", "unhappy", "disappointed", "cancel", "broken"}
_POSITIVE_WORDS = {"thanks", "thank", "great", "perfect", "excellent", "happy", "love", "awesome", "good"}
_URGENT_WORDS = {"urgent", "asap", "immediately", "now", "today", "emergency", "critical"}
_LOW_URGENCY_WORDS = {"whenever", "no rush", "no hurry", "eventually"}

_INTENT_KEYWORDS = {
    "pricing_inquiry": {"price", "cost", "quote", "how much", "pricing"},
    "availability_inquiry": {"stock", "available", "availability", "in stock"},
    "complaint": {"complaint", "problem", "refund", "broken", "unhappy", "disappointed"},
    "order_status": {"order", "delivery", "status", "shipment", "when will"},
    "scheduling": {"schedule", "appointment", "visit", "measurement"},
}

_SOURCE_QUALITY_BONUS = {
    "referral": 20,
    "website": 10,
    "whatsapp": 8,
    "instagram": 8,
    "office_visit": 15,
    "phone_call": 5,
    "messenger": 5,
    "facebook": 5,
    "other": -10,
}

_SOURCE_NEXT_ACTION = {
    "whatsapp": "Reply on WhatsApp within the hour",
    "instagram": "Reply to the Instagram DM within the hour",
    "messenger": "Reply on Messenger within the hour",
    "facebook": "Reply on Facebook within the hour",
    "phone_call": "Call the lead back today",
    "website": "Send a personalized quote based on their inquiry",
    "office_visit": "Schedule an in-person consultation",
    "referral": "Call to thank them and schedule a consultation",
    "other": "Send an introductory follow-up email",
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class MockAIProvider(AIProvider):
    name = "mock"
    model = "mock-heuristic-v1"

    # ── CRM Intelligence ─────────────────────────────────────────────────

    def analyze_lead(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        lead = context["lead"]
        other_leads = context.get("other_leads", [])
        customers = context.get("customers", [])

        score = 50
        score += _SOURCE_QUALITY_BONUS.get(lead.get("source_channel"), 0)
        if lead.get("email"):
            score += 12
        if lead.get("phone"):
            score += 12
        if lead.get("campaign"):
            score += 8
        score = int(_clamp(score, 0, 100))

        win_probability = round(score / 100, 2)

        if score >= 80:
            priority = "urgent"
        elif score >= 60:
            priority = "high"
        elif score >= 35:
            priority = "medium"
        else:
            priority = "low"

        next_action = _SOURCE_NEXT_ACTION.get(lead.get("source_channel"), _SOURCE_NEXT_ACTION["other"])
        follow_up_due_in_days = 1 if priority in ("urgent", "high") else 3

        missing_fields = [f for f in ("email", "phone") if not lead.get(f)]

        duplicates = [
            other["id"]
            for other in other_leads
            if other["id"] != lead["id"]
            and (
                (lead.get("email") and other.get("email") == lead.get("email"))
                or (lead.get("phone") and other.get("phone") == lead.get("phone"))
            )
        ]

        similar_customers = [
            customer["id"]
            for customer in customers
            if (lead.get("email") and customer.get("email") == lead.get("email"))
            or (lead.get("phone") and customer.get("phone") == lead.get("phone"))
            or (customer.get("name") and lead.get("full_name") and _shares_a_word(customer["name"], lead["full_name"]))
        ]

        explanation_bits = [f"Base score adjusted for source '{lead.get('source_channel', 'unknown')}'."]
        if lead.get("email") and lead.get("phone"):
            explanation_bits.append("Both email and phone are on file, which raises reachability confidence.")
        elif missing_fields:
            explanation_bits.append(f"Missing {', '.join(missing_fields)} lowers reachability confidence.")
        if duplicates:
            explanation_bits.append(f"{len(duplicates)} potential duplicate lead(s) detected.")
        if similar_customers:
            explanation_bits.append("Matches an existing customer record on contact details or name.")

        return AIAnalysisResult(
            data={
                "score": score,
                "win_probability": win_probability,
                "priority": priority,
                "next_best_action": next_action,
                "follow_up": {"due_in_days": follow_up_due_in_days, "note": f"Follow up with {lead.get('full_name', 'this lead')}"},
                "duplicate_lead_ids": duplicates,
                "similar_customer_ids": similar_customers,
                "missing_fields": missing_fields,
                "quality_explanation": " ".join(explanation_bits),
            },
            confidence=0.75 if (lead.get("email") or lead.get("phone")) else 0.5,
        )

    # ── Communication Intelligence ───────────────────────────────────────

    def analyze_conversation(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        messages: List[dict] = context.get("messages", [])
        text = "\n".join(m.get("body") or "" for m in messages)
        lowered = text.lower()

        if _CYRILLIC_RE.search(text):
            language = "ru"
        elif any(ch in _AZERBAIJANI_CHARS for ch in text):
            language = "az"
        else:
            language = "en"

        positive_hits = sum(1 for w in _POSITIVE_WORDS if w in lowered)
        negative_hits = sum(1 for w in _NEGATIVE_WORDS if w in lowered)
        if negative_hits > positive_hits:
            sentiment = "negative"
        elif positive_hits > negative_hits:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        if any(w in lowered for w in _URGENT_WORDS):
            urgency = "high"
        elif any(w in lowered for w in _LOW_URGENCY_WORDS):
            urgency = "low"
        else:
            urgency = "medium"

        intent = "general_inquiry"
        for candidate, keywords in _INTENT_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                intent = candidate
                break

        catalog_material_names: List[str] = context.get("catalog_material_names", [])
        product_names = sorted({name for name in catalog_material_names if name.lower() in lowered})

        phones = sorted(set(_PHONE_RE.findall(text)))
        emails = sorted(set(_EMAIL_RE.findall(text)))
        company_names = sorted(set(_COMPANY_SUFFIX_RE.findall(text)))
        addresses = sorted(set(_ADDRESS_HINT_RE.findall(text)))

        last_inbound = next((m for m in reversed(messages) if m.get("direction") == "inbound"), None)
        preview = (last_inbound or {}).get("body", "")[:150] if messages else ""
        summary = (
            f"{len(messages)}-message conversation, primarily about {intent.replace('_', ' ')}. "
            f"Sentiment: {sentiment}, urgency: {urgency}."
            + (f' Last message: "{preview}"' if preview else "")
        )

        link_suggestion: Optional[Dict[str, Any]] = None
        matched_customer = context.get("matched_customer")
        conversation = context.get("conversation", {})
        if not conversation.get("customer_id") and matched_customer:
            link_suggestion = {
                "entity_type": "customer",
                "entity_id": matched_customer["id"],
                "reason": "Extracted contact details match an existing Customer record.",
            }
        else:
            for key, entity_type in (("recent_project_id", "project"), ("recent_quote_id", "quote"), ("recent_order_id", "order")):
                if context.get(key) and not conversation.get(f"{entity_type}_id"):
                    link_suggestion = {
                        "entity_type": entity_type,
                        "entity_id": context[key],
                        "reason": f"The linked customer has a recent {entity_type} that isn't attached to this conversation yet.",
                    }
                    break

        return AIAnalysisResult(
            data={
                "language": language,
                "intent": intent,
                "sentiment": sentiment,
                "urgency": urgency,
                "summary": summary,
                "extracted": {
                    "phones": phones,
                    "emails": emails,
                    "company_names": company_names,
                    "addresses": addresses,
                    "product_names": product_names,
                },
                "link_suggestion": link_suggestion,
            },
            confidence=0.7 if messages else 0.3,
        )

    # ── Sales Intelligence ────────────────────────────────────────────────

    def analyze_quote(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        items: List[dict] = context.get("items", [])
        top_materials: List[dict] = context.get("top_materials", [])
        co_occurring: List[dict] = context.get("co_occurring_materials", [])
        upsell_candidates: List[dict] = context.get("upsell_candidates", [])
        avg_discount_pct: float = context.get("avg_discount_pct", 0.0)
        material_price_stats: Dict[str, dict] = context.get("material_price_stats", {})
        item_count = context.get("section_item_count", len(items))
        total_area_m2: float = context.get("total_area_m2", 0.0)

        current_material_ids = {i.get("material_id") for i in items if i.get("material_id")}

        product_recommendations = [
            m for m in top_materials if m["material_id"] not in current_material_ids
        ][:3]
        cross_sell = [
            m for m in co_occurring if m["material_id"] not in current_material_ids
        ][:3]
        upsell = [m for m in upsell_candidates if m["material_id"] not in current_material_ids][:3]

        discount_recommendation = {
            "suggested_pct": round(avg_discount_pct, 1),
            "rationale": f"This company's accepted quotes average a {round(avg_discount_pct, 1)}% discount.",
        }

        margin_risks = []
        price_anomalies = []
        for item in items:
            unit_sale = float(item.get("unit_sale_price") or 0)
            unit_cost = float(item.get("unit_cost_price") or 0)
            if unit_sale > 0:
                margin_pct = round((unit_sale - unit_cost) / unit_sale * 100, 1)
                if margin_pct < 15:
                    margin_risks.append({
                        "item_id": item["id"],
                        "description": item.get("description"),
                        "margin_pct": margin_pct,
                    })
            stats = material_price_stats.get(item.get("material_id") or "")
            if stats and stats.get("avg_sale_price"):
                avg_price = float(stats["avg_sale_price"])
                if avg_price > 0:
                    deviation_pct = round((unit_sale - avg_price) / avg_price * 100, 1)
                    if deviation_pct <= -30:
                        price_anomalies.append({"item_id": item["id"], "description": item.get("description"), "direction": "low", "deviation_pct": deviation_pct})
                    elif deviation_pct >= 30:
                        price_anomalies.append({"item_id": item["id"], "description": item.get("description"), "direction": "high", "deviation_pct": deviation_pct})

        if item_count <= 3 and total_area_m2 <= 15:
            delivery_complexity = "low"
        elif item_count <= 8 and total_area_m2 <= 40:
            delivery_complexity = "medium"
        else:
            delivery_complexity = "high"

        return AIAnalysisResult(
            data={
                "product_recommendations": product_recommendations,
                "cross_sell_suggestions": cross_sell,
                "upsell_suggestions": upsell,
                "discount_recommendation": discount_recommendation,
                "margin_risks": margin_risks,
                "price_anomalies": price_anomalies,
                "delivery_complexity": delivery_complexity,
            },
            confidence=0.65,
        )

    # ── Task Intelligence ─────────────────────────────────────────────────

    def suggest_tasks(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        stale_leads: List[dict] = context.get("stale_leads", [])
        stale_conversations: List[dict] = context.get("stale_conversations", [])
        workload: Dict[str, int] = context.get("user_workload", {})
        at_risk_tasks: List[dict] = context.get("at_risk_tasks", [])

        suggested_assignee = min(workload, key=workload.get) if workload else None

        tasks = []
        for lead in stale_leads:
            tasks.append({
                "title": f"Follow up with lead {lead.get('full_name', '')}".strip(),
                "priority": "high",
                "due_in_days": 1,
                "related_entity_type": "lead",
                "related_entity_id": lead["id"],
                "suggested_assignee": suggested_assignee,
            })
        for conv in stale_conversations:
            tasks.append({
                "title": f"Reply to conversation with {conv.get('external_contact_name') or conv.get('external_contact_id')}",
                "priority": "medium",
                "due_in_days": 1,
                "related_entity_type": "conversation",
                "related_entity_id": conv["id"],
                "suggested_assignee": suggested_assignee,
            })

        reminders = [
            {
                "title": f"Reminder: {t['title']}",
                "remind_in_days": max(t["due_in_days"] - 1, 0),
                "related_entity_type": t["related_entity_type"],
                "related_entity_id": t["related_entity_id"],
            }
            for t in tasks
        ]

        overdue_risks = [
            {
                "task_id": t["id"],
                "title": t.get("title"),
                "reason": "Due date is within 24 hours and the task is still pending.",
            }
            for t in at_risk_tasks
        ]

        return AIAnalysisResult(
            data={
                "tasks": tasks,
                "reminders": reminders,
                "assignee_suggestion": suggested_assignee,
                "overdue_risks": overdue_risks,
            },
            confidence=0.6,
        )

    # ── AI draft generation (Phase 21 follow-through) ────────────────────

    def draft_conversation_reply(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        # Reuses analyze_conversation's own language/intent/extraction
        # heuristics (a pure computation over the same context, no side
        # effects) rather than re-deriving them, so the two stay consistent
        # by construction instead of by convention.
        analysis = self.analyze_conversation(prompt=prompt, context=context)
        d = analysis.data
        language = d["language"] if d["language"] in _REPLY_TEMPLATES else "en"
        intent = d["intent"] if d["intent"] in _REPLY_TEMPLATES[language] else "general_inquiry"
        contact_name = (context.get("conversation") or {}).get("external_contact_name")
        name = contact_name or _REPLY_GREETING_NAME_FALLBACK[language]
        product_names = d["extracted"]["product_names"]
        product_phrase = f"{product_names[0]} " if product_names else ""
        draft_reply = _REPLY_TEMPLATES[language][intent].format(name=name, product_phrase=product_phrase)
        return AIAnalysisResult(
            data={"draft_reply": draft_reply, "reply_language": language},
            confidence=analysis.confidence,
        )

    def draft_quote_line_items(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        items: List[dict] = context.get("items", [])
        drafted = []
        for item in items:
            label = item.get("item_name") or item.get("material_name") or "Item"
            room = item.get("room_name")
            description = f"{label} — {room}" if room else label
            # Area-based stone pieces (m2) routinely need a cutting/offcut
            # waste allowance; simple per-unit accessories don't -- a real,
            # inspectable rule over the item's own recorded unit, not a
            # guess.
            waste_factor_pct = 10 if item.get("unit") == "m2" else 0
            drafted.append({
                "project_item_id": item["project_item_id"],
                "description": description,
                "waste_factor_pct": waste_factor_pct,
            })
        return AIAnalysisResult(
            data={"items": drafted},
            confidence=0.6 if items else 0.3,
        )


_REPLY_GREETING_NAME_FALLBACK = {"en": "there", "az": "hörmətli müştəri", "ru": "уважаемый клиент"}

_REPLY_TEMPLATES = {
    "en": {
        "pricing_inquiry": "Hi {name}, thanks for reaching out about {product_phrase}pricing. Could you share the room dimensions (or send your measurements) so we can prepare an accurate quote?",
        "availability_inquiry": "Hi {name}, thanks for checking in. Let us confirm current stock on {product_phrase}and get back to you with availability shortly.",
        "complaint": "Hi {name}, I'm sorry to hear about this. We want to make it right -- could you share a few more details (and photos if possible) so we can resolve it as quickly as possible?",
        "order_status": "Hi {name}, thanks for your patience. Let us check the current status of your order and update you shortly.",
        "scheduling": "Hi {name}, happy to help schedule that. What days/times work best for you this week?",
        "general_inquiry": "Hi {name}, thanks for your message! How can we help you today?",
    },
    "az": {
        "pricing_inquiry": "Salam {name}, {product_phrase}üçün qiymət sorğunuza görə təşəkkürlər. Dəqiq təklif hazırlaya bilməyimiz üçün ölçüləri bizimlə paylaşa bilərsinizmi?",
        "availability_inquiry": "Salam {name}, sorğunuza görə təşəkkürlər. {product_phrase}üçün anbar mövcudluğunu yoxlayıb qısa zamanda sizə məlumat verəcəyik.",
        "complaint": "Salam {name}, narahatlığınız üçün üzr istəyirik. Məsələni həll etmək üçün daha ətraflı məlumat (mümkünsə şəkillər) paylaşa bilərsinizmi?",
        "order_status": "Salam {name}, gözlədiyiniz üçün təşəkkürlər. Sifarişinizin statusunu yoxlayıb tezliklə sizə məlumat verəcəyik.",
        "scheduling": "Salam {name}, təyinat üçün məmnuniyyətlə kömək edərik. Bu həftə hansı gün/saat sizə uyğundur?",
        "general_inquiry": "Salam {name}, mesajınız üçün təşəkkürlər! Sizə necə kömək edə bilərik?",
    },
    "ru": {
        "pricing_inquiry": "Здравствуйте, {name}! Спасибо за интерес к цене на {product_phrase}. Не могли бы вы прислать размеры, чтобы мы подготовили точное предложение?",
        "availability_inquiry": "Здравствуйте, {name}! Спасибо за обращение. Уточним наличие {product_phrase}и скоро вернёмся с ответом.",
        "complaint": "Здравствуйте, {name}! Приносим извинения за неудобства. Не могли бы вы прислать подробности (и фото, если возможно), чтобы мы могли быстрее решить вопрос?",
        "order_status": "Здравствуйте, {name}! Спасибо за терпение. Уточним статус вашего заказа и скоро сообщим вам.",
        "scheduling": "Здравствуйте, {name}! С радостью поможем с записью. Какие дни/время вам удобны на этой неделе?",
        "general_inquiry": "Здравствуйте, {name}! Спасибо за сообщение. Чем можем помочь?",
    },
}


def _shares_a_word(a: str, b: str) -> bool:
    a_words = {w.lower() for w in a.split() if len(w) > 2}
    b_words = {w.lower() for w in b.split() if len(w) > 2}
    return bool(a_words & b_words)
