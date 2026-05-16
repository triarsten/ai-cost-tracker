import logging

logger = logging.getLogger(__name__)


def configure_opentelemetry() -> None:
    from django.conf import settings

    if not getattr(settings, "OTEL_ENABLED", False):
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        DjangoInstrumentor().instrument()
        CeleryInstrumentor().instrument()

        logger.info("OpenTelemetry configured", extra={"service": settings.OTEL_SERVICE_NAME})
    except Exception:
        logger.exception("Failed to configure OpenTelemetry")
