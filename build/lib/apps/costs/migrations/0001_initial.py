import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("display_name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="CostRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cost_records",
                        to="costs.provider",
                    ),
                ),
                ("date", models.DateField()),
                ("model_name", models.CharField(max_length=100)),
                ("input_tokens", models.BigIntegerField(default=0)),
                ("output_tokens", models.BigIntegerField(default=0)),
                ("cost_usd", models.DecimalField(decimal_places=6, max_digits=10)),
                ("synced_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="SyncLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_logs",
                        to="costs.provider",
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("failure", "Failure"), ("running", "Running")],
                        default="running",
                        max_length=20,
                    ),
                ),
                ("records_created", models.IntegerField(default=0)),
                ("records_updated", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="costrecord",
            index=models.Index(fields=["provider", "date"], name="costs_costr_provide_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="costrecord",
            unique_together={("provider", "date", "model_name")},
        ),
    ]
