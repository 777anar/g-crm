CATALOG_SETTINGS_SCHEMA = {
    "suggested_material_types": {
        "type": "array",
        "items": {"type": "string"},
        "default": [
            "Sintered Stone",
            "Porcelain",
            "Quartz",
            "Natural Marble",
            "Natural Granite",
            "Dekton",
            "Ceramic",
        ],
        "description": "Material types offered by default when creating a Stone Material.",
    },
    "default_currency": {
        "type": "string",
        "default": "AZN",
        "description": "Default currency for new price lists.",
    },
}
