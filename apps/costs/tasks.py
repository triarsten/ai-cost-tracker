import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

PROVIDER_REGISTRY: dict[str, type] = {}


def _get_provider_registry() -> dict[str, type]:
    if not PROVIDER_REGISTRY:
        from .providers.anthropic_provider import AnthropicProvider
        from .providers.fireworks_provider import FireworksProvider
        from .providers.gemini_provider import GeminiProvider

        PROVIDER_REGISTRY.update(
            {
                "anthropic": AnthropicProvider,
                "fireworks": FireworksProvider,
                "gemini": GeminiProvider,
            }
        )
    return PROVIDER_REGISTRY


@shared_task(bind=True, max_retries=3)
def sync_provider(self, provider_id: int, days_back: int = 7):
    from .models import CostRecord, Provider, SyncLog

    try:
        provider_obj = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        logger.error("Provider %s not found", provider_id)
        return

    sync_log = SyncLog.objects.create(provider=provider_obj)

    try:
        registry = _get_provider_registry()
        provider_class = registry.get(provider_obj.name)
        if provider_class is None:
            raise ValueError(f"No handler registered for provider '{provider_obj.name}'")

        handler = provider_class()
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        entries = handler.fetch_costs(start_date, end_date)

        created_count = 0
        updated_count = 0
        for entry in entries:
            _, created = CostRecord.objects.update_or_create(
                provider=provider_obj,
                date=entry.date,
                model_name=entry.model_name,
                defaults={
                    "input_tokens": entry.input_tokens,
                    "output_tokens": entry.output_tokens,
                    "cost_usd": entry.cost_usd,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        sync_log.status = SyncLog.Status.SUCCESS
        sync_log.records_created = created_count
        sync_log.records_updated = updated_count
        sync_log.finished_at = timezone.now()
        sync_log.save()

        logger.info(
            "Sync completed for provider %s: %d created, %d updated",
            provider_obj.name,
            created_count,
            updated_count,
        )

    except Exception as exc:
        sync_log.status = SyncLog.Status.FAILURE
        sync_log.error_message = str(exc)
        sync_log.finished_at = timezone.now()
        sync_log.save()

        logger.exception("Sync failed for provider %s", provider_obj.name)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc


@shared_task
def sync_all_providers(days_back: int = 7):
    from .models import Provider

    providers = Provider.objects.filter(is_active=True)
    for provider_obj in providers:
        sync_provider.delay(provider_obj.id, days_back=days_back)
        logger.info("Queued sync for provider %s", provider_obj.name)
