CRM_SETTINGS_SCHEMA = {
    "lead_source_channels": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["instagram", "facebook", "messenger", "whatsapp", "manual"],
        "description": "Lead capture channels enabled for this company.",
    }
}
