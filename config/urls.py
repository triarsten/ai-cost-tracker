from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("apps.health.urls")),
    path("metrics/", include("apps.metrics.urls")),  # "metrics/" statt "metrics/ai/"
    path("", include("django_prometheus.urls")),
]
