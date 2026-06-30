import uuid

import pytest

from core.events.event_bus import EventBus
from core.events.event_envelope import Event


def test_publish_calls_subscribed_handlers(monkeypatch):
    bus = EventBus()
    monkeypatch.setattr(bus, "_persist", lambda event: None)

    received = []
    bus.subscribe("LeadCreated", lambda event: received.append(event))

    event = Event(name="LeadCreated", company_id=uuid.uuid4(), payload={"lead_id": "abc"}, published_by_module="crm")
    bus.publish(event)

    assert len(received) == 1
    assert received[0].payload == {"lead_id": "abc"}


def test_publish_rejects_event_without_company_id(monkeypatch):
    bus = EventBus()
    monkeypatch.setattr(bus, "_persist", lambda event: None)

    with pytest.raises(ValueError):
        bus.publish(Event(name="LeadCreated", company_id=None, payload={}, published_by_module="crm"))


def test_handler_exception_does_not_break_other_handlers(monkeypatch):
    bus = EventBus()
    monkeypatch.setattr(bus, "_persist", lambda event: None)

    received = []
    bus.subscribe("OrderApproved", lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("OrderApproved", lambda event: received.append(event))

    bus.publish(Event(name="OrderApproved", company_id=uuid.uuid4(), payload={}, published_by_module="sales"))

    assert len(received) == 1
