"""Declarative base ONLY. No business models may be defined here.

Per the frozen architecture, this module is part of the core and must never
import from `modules.*`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
