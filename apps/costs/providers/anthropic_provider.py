# apps/costs/providers/anthropic_provider.py

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

import requests
from django.conf import settings

from .base import BaseProvider, CostEntry

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
REQUEST_TIMEOUT = 30

# Preise per Million Tokens (Stand Mai 2026)
MODEL_PRICES = {
    "claude-opus-4": {"input": Decimal("5.00"), "output": Decimal("25.00")},
    "claude-sonnet-4-6": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "claude-sonnet-4-5": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "claude-haiku-4-5": {"input": Decimal("1.00"), "output": Decimal("5.00")},
    "claude-haiku-4": {"input": Decimal("1.00"), "output": Decimal("5.00")},
}


def _get_price(model_name: str) -> tuple[Decimal, Decimal]:
    """Gibt (input_price, output_price) per Million Tokens zurück."""
    for prefix, prices in MODEL_PRICES.items():
        if model_name.startswith(prefix):
            return prices["input"], prices["output"]
    # Fallback: Sonnet-Preise
    logger.warning("Unbekanntes Modell %s, nutze Sonnet-Preise als Fallback", model_name)
    return Decimal("3.00"), Decimal("15.00")


class AnthropicProvider(BaseProvider):
    provider_name = "anthropic"

    def __init__(self) -> None:
        self.api_key = settings.ANTHROPIC_ADMIN_API_KEY
        self._session = requests.Session()
        self._session.headers.update(
            {
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            }
        )

    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        if not self.api_key:
            logger.warning("ANTHROPIC_ADMIN_API_KEY not set, skipping fetch")
            return []

        url = f"{ANTHROPIC_API_BASE}/v1/organizations/usage_report/messages"
        entries: list[CostEntry] = []

        params: dict = {
            "starting_at": f"{start_date.isoformat()}T00:00:00Z",
            "ending_at": f"{end_date.isoformat()}T23:59:59Z",
            "bucket_width": "1d",
            "group_by[]": "model",
        }

        while True:
            try:
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
            except requests.HTTPError as exc:
                logger.error("Anthropic API HTTP error: %s", exc)
                raise

            for bucket in data.get("data", []):
                # Datum aus starting_at des Buckets
                try:
                    entry_date = (
                        datetime.fromisoformat(bucket["starting_at"].replace("Z", "+00:00")).astimezone(UTC).date()
                    )
                except (KeyError, ValueError) as exc:
                    logger.warning("Skipping bucket with invalid date: %s", exc)
                    continue

                # Ergebnisse innerhalb des Buckets iterieren
                for result in bucket.get("results", []):
                    try:
                        model = result.get("model") or "unknown"

                        # Token-Felder laut echter API-Response
                        uncached_input = int(result.get("uncached_input_tokens", 0) or 0)
                        cache_read = int(result.get("cache_read_input_tokens", 0) or 0)
                        cache_creation = result.get("cache_creation") or {}
                        cache_write_1h = int(cache_creation.get("ephemeral_1h_input_tokens", 0) or 0)
                        cache_write_5m = int(cache_creation.get("ephemeral_5m_input_tokens", 0) or 0)
                        output_tokens = int(result.get("output_tokens", 0) or 0)

                        # Effektive Input-Tokens = uncached + cache_read + cache_write
                        total_input = uncached_input + cache_read + cache_write_1h + cache_write_5m

                        if total_input == 0 and output_tokens == 0:
                            continue

                        # Kosten berechnen
                        input_price, output_price = _get_price(model)

                        # Cache-Preise: read = 10% von input, write_5m = 125%, write_1h = 200%
                        cost_usd = (
                            Decimal(uncached_input) / Decimal("1000000") * input_price
                            + Decimal(cache_read) / Decimal("1000000") * input_price * Decimal("0.10")
                            + Decimal(cache_write_5m) / Decimal("1000000") * input_price * Decimal("1.25")
                            + Decimal(cache_write_1h) / Decimal("1000000") * input_price * Decimal("2.00")
                            + Decimal(output_tokens) / Decimal("1000000") * output_price
                        )

                        entries.append(
                            CostEntry(
                                date=entry_date,
                                model_name=model,
                                input_tokens=total_input,
                                output_tokens=output_tokens,
                                cost_usd=cost_usd,
                            )
                        )

                    except (KeyError, ValueError) as exc:
                        logger.warning("Skipping malformed result: %s — %s", exc, result)

            if data.get("has_more") and data.get("next_page"):
                params["page"] = data["next_page"]
            else:
                break

        logger.info("Fetched %d cost entries from Anthropic", len(entries))
        return entries

    def validate_credentials(self) -> bool:
        if not self.api_key:
            return False
        try:
            r = self._session.get(
                f"{ANTHROPIC_API_BASE}/v1/organizations",
                timeout=REQUEST_TIMEOUT,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False
