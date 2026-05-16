import logging
import time
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings

from .base import BaseProvider, CostEntry

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
REQUEST_TIMEOUT = 30


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

    def _request_with_retry(self, url: str, params: dict) -> dict:
        for attempt in range(3):
            try:
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if response.status_code == 429:
                    wait = 2**attempt
                    logger.warning("Rate limited by Anthropic API, retrying in %ds", wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.Timeout:
                logger.warning("Anthropic API timeout on attempt %d", attempt + 1)
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
            except requests.HTTPError as exc:
                logger.error("Anthropic API HTTP error: %s", exc)
                raise
        raise RuntimeError("Max retries exceeded for Anthropic API")

    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        if not self.api_key:
            logger.warning("ANTHROPIC_ADMIN_API_KEY not set, skipping fetch")
            return []

        url = f"{ANTHROPIC_API_BASE}/v1/organizations/cost_report"
        entries: list[CostEntry] = []
        params: dict = {
            "starting_at": start_date.isoformat(),
            "ending_at": end_date.isoformat(),
            "group_by[]": "model",
        }

        while True:
            data = self._request_with_retry(url, params)
            for item in data.get("data", []):
                model = item.get("model", "unknown")
                for day_entry in item.get("usage", []):
                    try:
                        entry_date = date.fromisoformat(day_entry["date"])
                        entries.append(
                            CostEntry(
                                date=entry_date,
                                model_name=model,
                                input_tokens=int(day_entry.get("input_tokens", 0)),
                                output_tokens=int(day_entry.get("output_tokens", 0)),
                                cost_usd=Decimal(str(day_entry.get("cost_usd", "0"))),
                            )
                        )
                    except (KeyError, ValueError) as exc:
                        logger.warning("Skipping malformed cost entry: %s", exc)

            next_page = data.get("next_page")
            if not next_page:
                break
            params["page"] = next_page

        logger.info("Fetched %d cost entries from Anthropic", len(entries))
        return entries

    def validate_credentials(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = self._session.get(
                f"{ANTHROPIC_API_BASE}/v1/organizations",
                timeout=REQUEST_TIMEOUT,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
