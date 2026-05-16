from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.costs.models import CostRecord


@pytest.mark.django_db
def test_create_cost_record(provider):
    record = CostRecord.objects.create(
        provider=provider,
        date=date(2024, 1, 15),
        model_name="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.001234"),
    )
    assert record.pk is not None
    assert record.provider == provider
    assert record.model_name == "claude-sonnet-4-6"


@pytest.mark.django_db
def test_cost_record_unique_together(provider):
    CostRecord.objects.create(
        provider=provider,
        date=date(2024, 1, 15),
        model_name="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.001234"),
    )

    with pytest.raises(IntegrityError):
        CostRecord.objects.create(
            provider=provider,
            date=date(2024, 1, 15),
            model_name="claude-sonnet-4-6",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=Decimal("0.002468"),
        )


@pytest.mark.django_db
def test_cost_record_same_model_different_date(provider):
    CostRecord.objects.create(
        provider=provider,
        date=date(2024, 1, 15),
        model_name="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.001234"),
    )
    record2 = CostRecord.objects.create(
        provider=provider,
        date=date(2024, 1, 16),
        model_name="claude-sonnet-4-6",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=Decimal("0.002468"),
    )
    assert record2.pk is not None
    assert CostRecord.objects.filter(provider=provider).count() == 2


@pytest.mark.django_db
def test_provider_str(provider):
    assert str(provider) == "Anthropic"


@pytest.mark.django_db
def test_cost_record_str(provider):
    record = CostRecord.objects.create(
        provider=provider,
        date=date(2024, 1, 15),
        model_name="claude-haiku-4-5",
        input_tokens=500,
        output_tokens=100,
        cost_usd=Decimal("0.000100"),
    )
    assert "anthropic" in str(record)
    assert "claude-haiku-4-5" in str(record)
