from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class CostEntry:
    date: date
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class BaseProvider(ABC):
    provider_name: str  # Muss in Subklassen gesetzt werden

    @abstractmethod
    def fetch_costs(self, start_date: date, end_date: date) -> list[CostEntry]:
        """Holt Kostendaten vom Provider für den angegebenen Zeitraum."""
        ...

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Prüft ob die konfigurierten Credentials gültig sind."""
        ...
