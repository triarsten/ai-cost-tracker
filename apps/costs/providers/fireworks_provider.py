import csv
import logging
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings

from .base import BaseProvider, CostEntry

logger = logging.getLogger(__name__)

# TODO: Fireworks billing API noch nicht verfügbar, manueller CSV-Import nötig


class FireworksProvider(BaseProvider):
    provider_name = "fireworks"

    def __init__(self) -> None:
        self.api_key = settings.FIREWORKS_API_KEY

    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        # TODO: Fireworks billing API noch nicht verfügbar, manueller CSV-Import nötig
        logger.info("Fireworks fetch_costs called but no billing API available; use import_from_csv")
        return []

    def validate_credentials(self) -> bool:
        return bool(self.api_key)

    def import_from_csv(self, filepath: str) -> list[CostEntry]:
        """
        Parst das Fireworks-CSV-Export-Format.

        Erwartete Felder:
        email,start_time,end_time,usage_type,accelerator_type,accelerator_seconds,
        base_model_name,model_bucket,parameter_count,prompt_tokens,completion_tokens
        """
        entries: list[CostEntry] = []

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    start_time = datetime.fromisoformat(row["start_time"].replace("Z", "+00:00"))
                    entry_date = start_time.date()
                    model_name = row.get("base_model_name") or row.get("model_bucket") or "unknown"
                    prompt_tokens = int(row.get("prompt_tokens") or 0)
                    completion_tokens = int(row.get("completion_tokens") or 0)

                    # Kosten auf 0.0 setzen da Fireworks-Preisliste nicht im Code hinterlegt ist
                    cost_usd = Decimal("0.0")

                    entries.append(
                        CostEntry(
                            date=entry_date,
                            model_name=model_name,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens,
                            cost_usd=cost_usd,
                        )
                    )
                except (KeyError, ValueError) as exc:
                    logger.warning("Skipping malformed Fireworks CSV row: %s", exc)

        logger.info("Imported %d entries from Fireworks CSV %s", len(entries), filepath)
        return entries
