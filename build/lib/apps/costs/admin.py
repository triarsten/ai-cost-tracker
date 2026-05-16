from django.contrib import admin, messages

from .models import CostRecord, Provider, SyncLog


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "is_active", "created_at"]
    actions = ["sync_now"]

    @admin.action(description="Sync now (last 7 days)")
    def sync_now(self, request, queryset):
        from .tasks import sync_provider

        count = 0
        for provider in queryset:
            sync_provider.delay(provider.id, days_back=7)
            count += 1
        self.message_user(request, f"Sync gestartet für {count} Provider.", messages.SUCCESS)


@admin.register(CostRecord)
class CostRecordAdmin(admin.ModelAdmin):
    list_display = ["provider", "date", "model_name", "input_tokens", "output_tokens", "cost_usd"]
    list_filter = ["provider", "date"]
    date_hierarchy = "date"
    ordering = ["-date"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ["provider", "started_at", "status", "records_created", "records_updated", "error_message"]
    list_filter = ["provider", "status"]
    ordering = ["-started_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
