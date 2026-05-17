import logging
from datetime import date, datetime, timezone
from decimal import Decimal

import requests
from django.conf import settings

from .base import BaseProvider, CostEntry

logger = logging.getLogger(__name__)

# Preise per Million Tokens (Stand Mai 2026)
# https://ai.google.dev/gemini-api/docs/pricing
GEMINI_MODEL_PRICES = {
    "gemini-2.5-pro":       {"input": Decimal("1.25"),  "output": Decimal("10.00")},
    "gemini-2.5-flash":     {"input": Decimal("0.30"),  "output": Decimal("2.50")},
    "gemini-2.5-flash-lite":{"input": Decimal("0.10"),  "output": Decimal("0.40")},
    "gemini-3-flash":       {"input": Decimal("0.50"),  "output": Decimal("3.00")},
    "gemini-3.1-pro":       {"input": Decimal("2.00"),  "output": Decimal("12.00")},
    "gemini-3.1-flash":     {"input": Decimal("0.50"),  "output": Decimal("3.00")},
    "gemini-3.1-flash-lite":{"input": Decimal("0.25"),  "output": Decimal("1.00")},
}

def _get_gemini_price(model_name: str) -> tuple[Decimal, Decimal]:
    model_lower = model_name.lower()
    for prefix, prices in GEMINI_MODEL_PRICES.items():
        if prefix in model_lower:
            return prices["input"], prices["output"]
    logger.warning("Unbekanntes Gemini-Modell %s, nutze Flash-Preise als Fallback", model_name)
    return Decimal("0.30"), Decimal("2.50")


class GeminiProvider(BaseProvider):
    """
    Gemini Developer API Provider.

    Nutzt die Google Cloud Billing API um Kostendaten abzurufen.
    Benötigt:
    - GEMINI_API_KEY: API-Key für die Gemini Developer API
    - GEMINI_BILLING_ACCOUNT_ID: Google Cloud Billing Account ID (z.B. "XXXXXX-XXXXXX-XXXXXX")
    - GEMINI_SERVICE_ACCOUNT_JSON: Pfad zur Service Account JSON-Datei mit Billing-Leserechten
      ODER GEMINI_ACCESS_TOKEN für einen manuell generierten OAuth2 Access Token

    Da die Google Cloud Billing API OAuth2 erfordert (kein einfacher API-Key),
    gibt es zwei Optionen:
    Option A (empfohlen): Service Account JSON → wird automatisch zu OAuth2 Token
    Option B (einfacher): Manuell generierten Access Token via gcloud CLI:
        gcloud auth print-access-token
    """
    provider_name = "gemini"

    BILLING_API_BASE = "https://cloudbilling.googleapis.com/v1"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
        self.billing_account_id = getattr(settings, "GEMINI_BILLING_ACCOUNT_ID", "") or ""
        self.access_token = getattr(settings, "GEMINI_ACCESS_TOKEN", "") or ""
        self.service_account_json = getattr(settings, "GEMINI_SERVICE_ACCOUNT_JSON", "") or ""

    def _get_access_token(self) -> str | None:
        """OAuth2 Access Token holen — via Service Account oder manuell gesetzt."""
        if self.access_token:
            return self.access_token

        if self.service_account_json:
            try:
                import google.auth
                import google.auth.transport.requests
                from google.oauth2 import service_account

                creds = service_account.Credentials.from_service_account_file(
                    self.service_account_json,
                    scopes=["https://www.googleapis.com/auth/cloud-billing.readonly"],
                )
                creds.refresh(google.auth.transport.requests.Request())
                return creds.token
            except Exception as exc:
                logger.error("Konnte Service Account Token nicht holen: %s", exc)
                return None

        return None

    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        if not self.billing_account_id:
            logger.warning("GEMINI_BILLING_ACCOUNT_ID nicht gesetzt, überspringe Gemini-Sync")
            return []

        token = self._get_access_token()
        if not token:
            logger.warning("Kein OAuth2 Token für Gemini Billing API verfügbar")
            return []

        # Google Cloud Billing API — Services für das Billing Account abrufen
        # Dann Usage nach Datum filtern
        url = (
            f"{self.BILLING_API_BASE}/billingAccounts/"
            f"{self.billing_account_id}/skus"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Vereinfachter Ansatz: BigQuery-Export oder Cloud Billing API
        # Die Cloud Billing API liefert SKU-Definitionen, aber keine tagesgenauen Kosten.
        # Für tagesgenaue Kosten brauchen wir entweder:
        # 1. BigQuery-Export des Billing-Buckets (komplex, aber vollständig)
        # 2. Cloud Billing Reports API (v1beta — noch in Preview)
        #
        # Interim-Lösung: Kosten aus Response-Metadaten der letzten API-Calls schätzen
        # TODO: BigQuery-Export implementieren für produktionsreife Kostendaten

        logger.info(
            "Gemini Billing API: Direkter tagesgenaue Abruf über Cloud Billing API "
            "erfordert BigQuery-Export. Bitte GEMINI_ACCESS_TOKEN oder Service Account "
            "konfigurieren "
