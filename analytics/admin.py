from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import MetricSnapshot


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("captured_at",)
    ordering = ("-captured_at",)