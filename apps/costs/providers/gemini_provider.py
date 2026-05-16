import logging
from datetime import date

from django.conf import settings

from .base import BaseProvider, CostEntry

logger = logging.getLogger(__name__)

# TODO: Implementierung nach Festlegung der Gemini-Variante (Developer API vs Vertex AI)


class GeminiProvider(BaseProvider):
    provider_name = "gemini"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or ""

    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        # TODO: Implementierung nach Festlegung der Gemini-Variante (Developer API vs Vertex AI)
        logger.info("GeminiProvider.fetch_costs: not yet implemented")
        return []

    def validate_credentials(self) -> bool:
        return bool(self.api_key)
