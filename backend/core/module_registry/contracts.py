"""The module contract. Every plugin module (CRM, Sales, Inventory, ...)
declares one `ModuleManifest`. The core only ever interacts with modules
through this shape -- it never imports a module's internal domain/
application/infrastructure code directly.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from fastapi import APIRouter


@dataclass
class ModuleManifest:
    name: str
    version: str
    router: APIRouter
    permissions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    navigation: List[dict] = field(default_factory=list)
    settings_schema: Optional[dict] = None
    jobs: List[Callable] = field(default_factory=list)
    event_subscriptions: Dict[str, List[Callable]] = field(default_factory=dict)
    models_package: Optional[str] = None
    migrations_path: Optional[str] = None
