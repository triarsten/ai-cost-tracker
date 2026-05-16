from django.urls import path

from .views import ai_metrics

urlpatterns = [
    path("ai/", ai_metrics, name="ai-metrics"),
]
