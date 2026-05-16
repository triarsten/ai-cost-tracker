from django.db import models


class Provider(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name

    class Meta:
        ordering = ["name"]


class CostRecord(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="cost_records")
    date = models.DateField()
    model_name = models.CharField(max_length=100)
    input_tokens = models.BigIntegerField(default=0)
    output_tokens = models.BigIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    synced_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.provider.name}/{self.model_name} {self.date}"

    class Meta:
        unique_together = [("provider", "date", "model_name")]
        indexes = [models.Index(fields=["provider", "date"])]
        ordering = ["-date"]


class SyncLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        RUNNING = "running", "Running"

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="sync_logs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.provider.name} {self.started_at:%Y-%m-%d %H:%M} [{self.status}]"

    class Meta:
        ordering = ["-started_at"]
