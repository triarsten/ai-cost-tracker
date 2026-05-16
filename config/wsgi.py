import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# OTel darf nicht im Master-Prozess initialisiert werden — nur in Gunicorn-Workern
# (post_fork Hook in gunicorn.conf.py). Hier nur initialisieren wenn wir NICHT unter Gunicorn laufen.
if not os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
    from config.telemetry import configure_opentelemetry

    configure_opentelemetry()

application = get_wsgi_application()
