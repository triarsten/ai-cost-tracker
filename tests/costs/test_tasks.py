from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.costs.providers.base import CostEntry


@pytest.fixture
def anthropic_provider(db):
    from apps.costs.models import Provider

    return Provider.objects.create(name="anthropic", display_name="Anthropic", is_active=True)


@pytest.mark.django_db
def test_sync_provider_success(anthropic_provider):
    mock_entries = [
        CostEntry(
            date=date(2024, 1, 15),
            model_name="claude-sonnet-4-6",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("0.01"),
        ),
        CostEntry(
            date=date(2024, 1, 16),
            model_name="claude-sonnet-4-6",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=Decimal("0.02"),
        ),
    ]

    mock_handler = MagicMock()
    mock_handler.fetch_costs.return_value = mock_entries

    with patch("apps.costs.tasks._get_provider_registry", return_value={"anthropic": lambda: mock_handler}):
        from apps.costs.tasks import sync_provider

        sync_provider(anthropic_provider.id, days_back=7)

    from apps.costs.models import CostRecord, SyncLog

    assert CostRecord.objects.filter(provider=anthropic_provider).count() == 2
    sync_log = SyncLog.objects.filter(provider=anthropic_provider, status="success").first()
    assert sync_log is not None
    assert sync_log.records_created == 2
    assert sync_log.records_updated == 0


@pytest.mark.django_db
def test_sync_provider_update_existing(anthropic_provider):
    from apps.costs.models import CostRecord

    CostRecord.objects.create(
        provider=anthropic_provider,
        date=date(2024, 1, 15),
        model_name="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.001"),
    )

    mock_entries = [
        CostEntry(
            date=date(2024, 1, 15),
            model_name="claude-sonnet-4-6",
            input_tokens=200,
            output_tokens=100,
            cost_usd=Decimal("0.002"),
        ),
    ]

    mock_handler = MagicMock()
    mock_handler.fetch_costs.return_value = mock_entries

    with patch("apps.costs.tasks._get_provider_registry", return_value={"anthropic": lambda: mock_handler}):
        from apps.costs.tasks import sync_provider

        sync_provider(anthropic_provider.id, days_back=7)

    from apps.costs.models import SyncLog

    record = CostRecord.objects.get(provider=anthropic_provider, date=date(2024, 1, 15))
    assert record.input_tokens == 200

    sync_log = SyncLog.objects.filter(provider=anthropic_provider, status="success").first()
    assert sync_log is not None
    assert sync_log.records_updated == 1
    assert sync_log.records_created == 0


@pytest.mark.django_db
def test_sync_provider_failure(anthropic_provider):
    from apps.costs.models import SyncLog
    from apps.costs.tasks import sync_provider

    mock_handler = MagicMock()
    mock_handler.fetch_costs.side_effect = RuntimeError("API error")

    with (
        patch("apps.costs.tasks._get_provider_registry", return_value={"anthropic": lambda: mock_handler}),
        patch.object(sync_provider, "retry", side_effect=RuntimeError("retry disabled in test")),
        pytest.raises(RuntimeError),
    ):
        sync_provider(anthropic_provider.id, days_back=7)

    sync_log = SyncLog.objects.filter(provider=anthropic_provider, status="failure").first()
    assert sync_log is not None
    assert "API error" in sync_log.error_message


@pytest.mark.django_db
def test_sync_provider_unknown_provider_id():
    from apps.costs.tasks import sync_provider

    sync_provider(99999, days_back=7)


@pytest.mark.django_db
def test_sync_all_providers(anthropic_provider):
    from apps.costs.models import Provider

    Provider.objects.create(name="fireworks", display_name="Fireworks", is_active=False)

    with patch("apps.costs.tasks.sync_provider") as mock_sync:
        mock_sync.delay = MagicMock()
        from apps.costs.tasks import sync_all_providers

        sync_all_providers(days_back=3)

    mock_sync.delay.assert_called_once_with(anthropic_provider.id, days_back=3)
