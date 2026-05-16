from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_ai_metrics_endpoint_returns_200(client):
    response = client.get("/metrics/ai/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ai_metrics_content_type(client):
    response = client.get("/metrics/ai/")
    assert "text/plain" in response["Content-Type"]


@pytest.mark.django_db
def test_ai_metrics_contains_expected_metrics(client):
    from apps.costs.models import CostRecord, Provider

    provider = Provider.objects.create(name="anthropic", display_name="Anthropic")
    CostRecord.objects.create(
        provider=provider,
        date=date.today() - timedelta(days=1),
        model_name="claude-sonnet-4-6",
        input_tokens=5000,
        output_tokens=1000,
        cost_usd=Decimal("0.012345"),
    )

    response = client.get("/metrics/ai/")
    content = response.content.decode("utf-8")

    assert "ai_cost_usd_total" in content
    assert "ai_tokens_total" in content
    assert "ai_cost_current_month_usd" in content
    assert 'provider="anthropic"' in content
    assert 'model="claude-sonnet-4-6"' in content


@pytest.mark.django_db
def test_ai_metrics_empty_db(client):
    response = client.get("/metrics/ai/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "ai_cost_usd_total" in content
