from datetime import date
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


def _make_bucket(date_str: str, model: str, input_tokens: int, output_tokens: int) -> dict:
    """Hilfsfunktion: Erzeugt einen API-Bucket im echten Format."""
    return {
        "starting_at": f"{date_str}T00:00:00Z",
        "ending_at": f"{date_str}T23:59:59Z",
        "results": [
            {
                "model": model,
                "uncached_input_tokens": input_tokens,
                "cache_creation": {
                    "ephemeral_1h_input_tokens": 0,
                    "ephemeral_5m_input_tokens": 0,
                },
                "cache_read_input_tokens": 0,
                "output_tokens": output_tokens,
                "server_tool_use": {"web_search_requests": 0},
            }
        ],
    }


def test_fetch_costs_returns_entries(provider):
    api_response = {
        "data": [_make_bucket("2024-01-15", "claude-sonnet-4-6", 10000, 2000)],
        "has_more": False,
    }

    with patch.object(provider._session, "get", return_value=_mock_response(api_response)):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert len(entries) == 1
    assert entries[0].model_name == "claude-sonnet-4-6"
    assert entries[0].input_tokens == 10000
    assert entries[0].output_tokens == 2000
    assert entries[0].date == date(2024, 1, 15)
    assert entries[0].cost_usd > 0


def test_fetch_costs_pagination(provider):
    page1 = {
        "data": [_make_bucket("2024-01-15", "claude-sonnet-4-6", 100, 50)],
        "has_more": True,
        "next_page": "page2token",
    }
    page2 = {
        "data": [_make_bucket("2024-01-16", "claude-haiku-4-5", 200, 100)],
        "has_more": False,
    }

    responses = [_mock_response(page1), _mock_response(page2)]
    with patch.object(provider._session, "get", side_effect=responses):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 16))

    assert len(entries) == 2
    models = {e.model_name for e in entries}
    assert "claude-sonnet-4-6" in models
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
    """Buckets mit leeren results werden übersprungen, valide werden verarbeitet."""
    api_response = {
        "data": [
            # Leerer Bucket — wird übersprungen
            {
                "starting_at": "2024-01-14T00:00:00Z",
                "ending_at": "2024-01-15T00:00:00Z",
                "results": [],
            },
            # Valider Bucket
            _make_bucket("2024-01-15", "claude-sonnet-4-6", 200, 80),
        ],
        "has_more": False,
    }
    with patch.object(provider._session, "get", return_value=_mock_response(api_response)):
        entries = provider.fetch_costs(date(2024, 1, 14), date(2024, 1, 15))

    assert len(entries) == 1
    assert entries[0].input_tokens == 200


def test_fetch_costs_with_cache_tokens(provider):
    """Cache-Tokens werden korrekt in die Kostenberechnung einbezogen."""
    api_response = {
        "data": [
            {
                "starting_at": "2024-01-15T00:00:00Z",
                "ending_at": "2024-01-16T00:00:00Z",
                "results": [
                    {
                        "model": "claude-sonnet-4-6",
                        "uncached_input_tokens": 1000,
                        "cache_creation": {
                            "ephemeral_1h_input_tokens": 0,
                            "ephemeral_5m_input_tokens": 500,
                        },
                        "cache_read_input_tokens": 2000,
                        "output_tokens": 300,
                        "server_tool_use": {"web_search_requests": 0},
                    }
                ],
            }
        ],
        "has_more": False,
    }
    with patch.object(provider._session, "get", return_value=_mock_response(api_response)):
        entries = provider.fetch_costs(date(2024, 1, 15), date(2024, 1, 15))

    assert len(entries) == 1
    # total_input = 1000 + 500 + 2000 = 3500
    assert entries[0].input_tokens == 3500
    assert entries[0].output_tokens == 300
    assert entries[0].cost_usd > 0
