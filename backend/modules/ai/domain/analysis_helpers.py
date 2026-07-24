"""Deterministic, non-LLM sub-computations used by the real `AnthropicProvider`
(Phase 21). Exact-ID matching (duplicate leads, similar customers), regex
extraction, and financial-threshold math (margin risk, price anomalies,
discount averages) are real-data lookups and arithmetic, not judgment calls a
language model should be asked to approximate -- asking an LLM to "recall"
a UUID risks a hallucinated id, and asking it to redo exact arithmetic a
database query already computed correctly adds risk for no benefit. These
functions give the real provider the same correct, inspectable answers for
that half of each analysis; the model is only asked for the genuinely
language/judgment-shaped half (score, sentiment, phrasing, ranking within an
already-real candidate list, ...).

`MockAIProvider` intentionally does not import these -- it re-derives the
same rules inline as its own deterministic heuristic stand-in for a real
model's judgment, and the two are allowed to diverge slightly without either
being "wrong" (mock is a heuristic proxy for the judgment half too, not just
the exact-match half this module covers).
"""
import re
from typing import Dict, List, Optional

_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3}[\s-]?\d{2,4}[\s-]?\d{0,4}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_COMPANY_SUFFIX_RE = re.compile(r"\b([A-Z][\w&.]*(?:\s+[A-Z][\w&.]*){0,3}\s+(?:MMC|LLC|Ltd\.?|Inc\.?|Co\.?))\b")
_ADDRESS_HINT_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9əöüğşçıİĞÖÜŞÇ.'\-]+\s+(?:str\.?|street|küç\.?|ave\.?|avenue|road|rd\.?)\b",
    re.IGNORECASE,
)
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_AZERBAIJANI_CHARS = set("əöüğşçıİĞÖÜŞÇıə")


def _shares_a_word(a: str, b: str) -> bool:
    a_words = {w.lower() for w in a.split() if len(w) > 2}
    b_words = {w.lower() for w in b.split() if len(w) > 2}
    return bool(a_words & b_words)


# ── CRM Intelligence ─────────────────────────────────────────────────────────


def find_duplicate_lead_ids(lead: dict, other_leads: List[dict]) -> List[str]:
    return [
        other["id"]
        for other in other_leads
        if other["id"] != lead["id"]
        and (
            (lead.get("email") and other.get("email") == lead.get("email"))
            or (lead.get("phone") and other.get("phone") == lead.get("phone"))
        )
    ]


def find_similar_customer_ids(lead: dict, customers: List[dict]) -> List[str]:
    return [
        customer["id"]
        for customer in customers
        if (lead.get("email") and customer.get("email") == lead.get("email"))
        or (lead.get("phone") and customer.get("phone") == lead.get("phone"))
        or (
            customer.get("name")
            and lead.get("full_name")
            and _shares_a_word(customer["name"], lead["full_name"])
        )
    ]


def missing_contact_fields(lead: dict) -> List[str]:
    return [f for f in ("email", "phone") if not lead.get(f)]


# ── Communication Intelligence ───────────────────────────────────────────────


def detect_language(text: str) -> str:
    if _CYRILLIC_RE.search(text):
        return "ru"
    if any(ch in _AZERBAIJANI_CHARS for ch in text):
        return "az"
    return "en"


def extract_conversation_entities(messages: List[dict], catalog_material_names: List[str]) -> dict:
    text = "\n".join(m.get("body") or "" for m in messages)
    lowered = text.lower()
    return {
        "phones": sorted(set(_PHONE_RE.findall(text))),
        "emails": sorted(set(_EMAIL_RE.findall(text))),
        "company_names": sorted(set(_COMPANY_SUFFIX_RE.findall(text))),
        "addresses": sorted(set(_ADDRESS_HINT_RE.findall(text))),
        "product_names": sorted({name for name in catalog_material_names if name.lower() in lowered}),
    }


def suggest_conversation_link(*, context: dict) -> Optional[dict]:
    matched_customer = context.get("matched_customer")
    conversation = context.get("conversation", {})
    if not conversation.get("customer_id") and matched_customer:
        return {
            "entity_type": "customer",
            "entity_id": matched_customer["id"],
            "reason": "Extracted contact details match an existing Customer record.",
        }
    for key, entity_type in (("recent_project_id", "project"), ("recent_quote_id", "quote"), ("recent_order_id", "order")):
        if context.get(key) and not conversation.get(f"{entity_type}_id"):
            return {
                "entity_type": entity_type,
                "entity_id": context[key],
                "reason": f"The linked customer has a recent {entity_type} that isn't attached to this conversation yet.",
            }
    return None


# ── Sales Intelligence ────────────────────────────────────────────────────────


def compute_discount_recommendation(avg_discount_pct: float) -> dict:
    return {
        "suggested_pct": round(avg_discount_pct, 1),
        "rationale": f"This company's accepted quotes average a {round(avg_discount_pct, 1)}% discount.",
    }


def compute_margin_risks(items: List[dict]) -> List[dict]:
    risks = []
    for item in items:
        unit_sale = float(item.get("unit_sale_price") or 0)
        unit_cost = float(item.get("unit_cost_price") or 0)
        if unit_sale > 0:
            margin_pct = round((unit_sale - unit_cost) / unit_sale * 100, 1)
            if margin_pct < 15:
                risks.append({"item_id": item["id"], "description": item.get("description"), "margin_pct": margin_pct})
    return risks


def compute_price_anomalies(items: List[dict], material_price_stats: Dict[str, dict]) -> List[dict]:
    anomalies = []
    for item in items:
        stats = material_price_stats.get(item.get("material_id") or "")
        if not stats or not stats.get("avg_sale_price"):
            continue
        avg_price = float(stats["avg_sale_price"])
        unit_sale = float(item.get("unit_sale_price") or 0)
        if avg_price <= 0:
            continue
        deviation_pct = round((unit_sale - avg_price) / avg_price * 100, 1)
        if deviation_pct <= -30:
            anomalies.append({"item_id": item["id"], "description": item.get("description"), "direction": "low", "deviation_pct": deviation_pct})
        elif deviation_pct >= 30:
            anomalies.append({"item_id": item["id"], "description": item.get("description"), "direction": "high", "deviation_pct": deviation_pct})
    return anomalies


def compute_delivery_complexity(*, item_count: int, total_area_m2: float) -> str:
    if item_count <= 3 and total_area_m2 <= 15:
        return "low"
    if item_count <= 8 and total_area_m2 <= 40:
        return "medium"
    return "high"


def select_candidates_by_id(candidates: List[dict], selected_ids: List[str], *, limit: int = 3) -> List[dict]:
    """Maps a real model's selection (material ids only) back to the full
    candidate dicts the use case already built from real data -- a selection
    outside the given candidate set (a hallucinated id) is silently dropped
    rather than fabricating a row for it."""
    by_id = {c["material_id"]: c for c in candidates}
    seen = set()
    result = []
    for material_id in selected_ids:
        if material_id in by_id and material_id not in seen:
            result.append(by_id[material_id])
            seen.add(material_id)
        if len(result) >= limit:
            break
    return result


# ── Task Intelligence ─────────────────────────────────────────────────────────


def compute_task_reminders(tasks: List[dict]) -> List[dict]:
    return [
        {
            "title": f"Reminder: {t['title']}",
            "remind_in_days": max(t["due_in_days"] - 1, 0),
            "related_entity_type": t["related_entity_type"],
            "related_entity_id": t["related_entity_id"],
        }
        for t in tasks
    ]


def suggest_assignee(workload: Dict[str, int]) -> Optional[str]:
    return min(workload, key=workload.get) if workload else None


def compute_overdue_risks(at_risk_tasks: List[dict]) -> List[dict]:
    return [
        {"task_id": t["id"], "title": t.get("title"), "reason": "Due date is within 24 hours and the task is still pending."}
        for t in at_risk_tasks
    ]
