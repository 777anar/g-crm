CRM_SETTINGS_SCHEMA = {
    "lead_source_channels": {
        "type": "array",
        "items": {"type": "string"},
        "default": [
            "instagram",
            "facebook",
            "messenger",
            "whatsapp",
            "phone_call",
            "website",
            "office_visit",
            "referral",
            "other",
        ],
        "description": "Lead sources enabled for this company (stone-industry workflow).",
    }
}
