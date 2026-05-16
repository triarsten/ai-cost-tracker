import logging
from datetime import date, timedelta

from django.db.models import Max, Sum
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def ai_metrics(request):
    from prometheus_client import CollectorRegistry, Gauge, generate_latest
    from prometheus_client.exposition import CONTENT_TYPE_LATEST

    from apps.costs.models import CostRecord, SyncLog

    registry = CollectorRegistry()

    cost_gauge = Gauge(
        "ai_cost_usd_total",
        "Total AI costs in USD for the last 30 days",
        ["provider", "model"],
        registry=registry,
    )
    tokens_gauge = Gauge(
        "ai_tokens_total",
        "Total AI tokens consumed",
        ["provider", "model", "type"],
        registry=registry,
    )
    sync_ts_gauge = Gauge(
        "ai_sync_last_success_timestamp",
        "Unix timestamp of last successful sync",
        ["provider"],
        registry=registry,
    )
    month_cost_gauge = Gauge(
        "ai_cost_current_month_usd",
        "AI costs for the current calendar month in USD",
        ["provider"],
        registry=registry,
    )

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    month_start = today.replace(day=1)

    rows_30d = (
        CostRecord.objects.filter(date__gte=thirty_days_ago)
        .values("provider__name", "model_name")
        .annotate(
            total_cost=Sum("cost_usd"),
            total_input=Sum("input_tokens"),
            total_output=Sum("output_tokens"),
        )
    )

    for row in rows_30d:
        provider = row["provider__name"]
        model = row["model_name"]
        cost_gauge.labels(provider=provider, model=model).set(float(row["total_cost"] or 0))
        tokens_gauge.labels(provider=provider, model=model, type="input").set(row["total_input"] or 0)
        tokens_gauge.labels(provider=provider, model=model, type="output").set(row["total_output"] or 0)

    rows_month = (
        CostRecord.objects.filter(date__gte=month_start)
        .values("provider__name")
        .annotate(total_cost=Sum("cost_usd"))
    )
    for row in rows_month:
        month_cost_gauge.labels(provider=row["provider__name"]).set(float(row["total_cost"] or 0))

    last_syncs = (
        SyncLog.objects.filter(status="success")
        .values("provider__name")
        .annotate(last_sync=Max("finished_at"))
    )
    for row in last_syncs:
        if row["last_sync"]:
            sync_ts_gauge.labels(provider=row["provider__name"]).set(row["last_sync"].timestamp())

    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
