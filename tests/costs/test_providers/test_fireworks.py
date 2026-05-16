import csv
import os
import tempfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.costs.providers.fireworks_provider import FireworksProvider


@pytest.fixture
def provider():
    with patch("apps.costs.providers.fireworks_provider.settings") as mock_settings:
        mock_settings.FIREWORKS_API_KEY = "fw_test_key"
        yield FireworksProvider()


def test_fetch_costs_returns_empty(provider):
    entries = provider.fetch_costs(date(2024, 1, 1), date(2024, 1, 31))
    assert entries == []


def _write_csv(path: str, rows: list[dict]) -> None:
    fieldnames = [
        "email",
        "start_time",
        "end_time",
        "usage_type",
        "accelerator_type",
        "accelerator_seconds",
        "base_model_name",
        "model_bucket",
        "parameter_count",
        "prompt_tokens",
        "completion_tokens",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_import_from_csv_basic(provider):
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        tmppath = f.name

    try:
        _write_csv(
            tmppath,
            [
                {
                    "email": "user@example.com",
                    "start_time": "2024-01-15T10:00:00Z",
                    "end_time": "2024-01-15T10:01:00Z",
                    "usage_type": "inference",
                    "accelerator_type": "A100",
                    "accelerator_seconds": "60",
                    "base_model_name": "llama-v3-70b",
                    "model_bucket": "fireworks/llama-v3-70b",
                    "parameter_count": "70000000000",
                    "prompt_tokens": "1500",
                    "completion_tokens": "350",
                }
            ],
        )

        entries = provider.import_from_csv(tmppath)
    finally:
        os.unlink(tmppath)

    assert len(entries) == 1
    assert entries[0].model_name == "llama-v3-70b"
    assert entries[0].input_tokens == 1500
    assert entries[0].output_tokens == 350
    assert entries[0].date == date(2024, 1, 15)
    assert entries[0].cost_usd == Decimal("0.0")


def test_import_from_csv_multiple_rows(provider):
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        tmppath = f.name

    try:
        _write_csv(
            tmppath,
            [
                {
                    "email": "a@b.com",
                    "start_time": "2024-01-15T10:00:00Z",
                    "end_time": "2024-01-15T10:01:00Z",
                    "usage_type": "inference",
                    "accelerator_type": "",
                    "accelerator_seconds": "0",
                    "base_model_name": "model-a",
                    "model_bucket": "",
                    "parameter_count": "",
                    "prompt_tokens": "100",
                    "completion_tokens": "50",
                },
                {
                    "email": "a@b.com",
                    "start_time": "2024-01-16T10:00:00Z",
                    "end_time": "2024-01-16T10:01:00Z",
                    "usage_type": "inference",
                    "accelerator_type": "",
                    "accelerator_seconds": "0",
                    "base_model_name": "model-b",
                    "model_bucket": "",
                    "parameter_count": "",
                    "prompt_tokens": "200",
                    "completion_tokens": "100",
                },
            ],
        )
        entries = provider.import_from_csv(tmppath)
    finally:
        os.unlink(tmppath)

    assert len(entries) == 2
    models = {e.model_name for e in entries}
    assert "model-a" in models
    assert "model-b" in models


def test_validate_credentials_with_key(provider):
    assert provider.validate_credentials() is True


def test_validate_credentials_without_key():
    with patch("apps.costs.providers.fireworks_provider.settings") as mock_settings:
        mock_settings.FIREWORKS_API_KEY = ""
        p = FireworksProvider()
        assert p.validate_credentials() is False
