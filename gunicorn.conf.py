import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()


# OTel muss nach dem Fork in jedem Worker initialisiert werden, nicht im Master.
# Initialisierung im Master würde dazu führen, dass alle Worker denselben Tracer-State teilen.
def post_fork(server, worker):
    from config.telemetry import configure_opentelemetry

    configure_opentelemetry()


def worker_exit(server, worker):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
