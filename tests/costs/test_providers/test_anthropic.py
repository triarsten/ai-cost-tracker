from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.costs.providers.anthropic_provider import AnthropicProvider


@pytest.fixture
def provider():
    with patch("apps.costs.providers.anthropic_provider.settings") as mock_settings:
        mock_settings.ANTHROPIC_ADMIN_API_KEY = "sk-ant-admin-test-key"
        p = AnthropicProvider()
        yield p


def _mock_response(data: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests import HTTPError

        mock.raise_for_status.side_effect = HTTPError(response=mock)
    return mock


def test_fetch_costs_returns_entries(provider):
    api_response = {
        "data": [
            {
                "model": "claude-sonnet-4-6",
                "usage": [
                    {
                        "date": "2024-01-15",
                        "input_tokens": 10000,
                        "output_tokens": 2000,
                        "cost_usd": "0.034500",
                    }
                ],
            }
        ],
    }

    with patch.object(provider._session, "get", return_value=_mock_response(api_response)):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert len(entries) == 1
    assert entries[0].model_name == "claude-sonnet-4-6"
    assert entries[0].input_tokens == 10000
    assert entries[0].output_tokens == 2000
    assert entries[0].cost_usd == Decimal("0.034500")
    assert entries[0].date == date(2024, 1, 15)


def test_fetch_costs_pagination(provider):
    page1 = {
        "data": [
            {
                "model": "claude-opus-4-7",
                "usage": [{"date": "2024-01-15", "input_tokens": 100, "output_tokens": 50, "cost_usd": "0.1"}],
            }
        ],
        "next_page": "page2token",
    }
    page2 = {
        "data": [
            {
                "model": "claude-haiku-4-5",
                "usage": [{"date": "2024-01-15", "input_tokens": 200, "output_tokens": 100, "cost_usd": "0.05"}],
            }
        ],
    }

    responses = [_mock_response(page1), _mock_response(page2)]
    with patch.object(provider._session, "get", side_effect=responses):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert len(entries) == 2
    models = {e.model_name for e in entries}
    assert "claude-opus-4-7" in models
    assert "claude-haiku-4-5" in models


def test_fetch_costs_empty_key():
    with patch("apps.costs.providers.anthropic_provider.settings") as mock_settings:
        mock_settings.ANTHROPIC_ADMIN_API_KEY = ""
        p = AnthropicProvider()
        entries = p.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert entries == []


def test_fetch_costs_http_error(provider):
    from requests import HTTPError

    mock_resp = _mock_response({}, status_code=500)
    with patch.object(provider._session, "get", return_value=mock_resp), pytest.raises(HTTPError):
        provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))


def test_fetch_costs_skips_malformed_entry(provider):
    api_response = {
        "data": [
            {
                "model": "claude-sonnet-4-6",
                "usage": [
                    {"date": "not-a-date", "input_tokens": 100, "output_tokens": 50, "cost_usd": "0.01"},
                    {"date": "2024-01-15", "input_tokens": 200, "output_tokens": 80, "cost_usd": "0.02"},
                ],
            }
        ],
    }
    with patch.object(provider._session, "get", return_value=_mock_response(api_response)):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert len(entries) == 1
    assert entries[0].input_tokens == 200
