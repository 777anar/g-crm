"""Pure domain-layer tests: no database, no HTTP server -- proving the
Clean Architecture claim that domain logic is testable in isolation."""
import uuid
from datetime import datetime, timezone

import pytest

from modules.crm.domain.entities import Customer, Lead
from modules.crm.domain.exceptions import CustomerAlreadyArchivedError, LeadAlreadyConvertedError


def _customer(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        name="Test Customer",
        type="business",
        primary_contact_id=None,
        assigned_manager_id=None,
        lead_source=None,
        advertising_campaign=None,
    )
    defaults.update(overrides)
    return Customer(**defaults)


def test_customer_is_not_archived_by_default():
    customer = _customer()
    assert customer.is_archived is False


def test_archiving_customer_sets_deleted_at():
    customer = _customer()
    now = datetime.now(timezone.utc)
    customer.archive(at=now)
    assert customer.is_archived is True
    assert customer.deleted_at == now


def test_archiving_already_archived_customer_raises():
    customer = _customer()
    customer.archive(at=datetime.now(timezone.utc))
    with pytest.raises(CustomerAlreadyArchivedError):
        customer.archive(at=datetime.now(timezone.utc))


def _lead(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        full_name="Test Lead",
        email=None,
        phone=None,
        source_channel="manual",
        campaign=None,
        status="new",
        assigned_manager_id=None,
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_lead_is_not_converted_by_default():
    lead = _lead()
    assert lead.is_converted is False


def test_converting_lead_sets_conversion_fields():
    lead = _lead()
    customer_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    lead.mark_converted(customer_id=customer_id, contact_id=contact_id, at=now)

    assert lead.is_converted is True
    assert lead.converted_customer_id == customer_id
    assert lead.converted_contact_id == contact_id
    assert lead.converted_at == now


def test_converting_already_converted_lead_raises():
    lead = _lead()
    lead.mark_converted(customer_id=uuid.uuid4(), contact_id=uuid.uuid4(), at=datetime.now(timezone.utc))
    with pytest.raises(LeadAlreadyConvertedError):
        lead.mark_converted(customer_id=uuid.uuid4(), contact_id=uuid.uuid4(), at=datetime.now(timezone.utc))
