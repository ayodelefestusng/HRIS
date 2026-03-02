# Register your models here.
# Register your models here.
from django.contrib import admin
from .models import ShiftSchedule,AttendanceRecord,OvertimeRecord,ClockLog
from django.utils.html import format_html

admin.site.register(ShiftSchedule)
# admin.site.register(AttendanceRecord)
admin.site.register(OvertimeRecord)
# admin.site.register(ClockLog)



# attendance/admin.py
@admin.register(ClockLog)
class ClockLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'action', 'timestamp', 'ip_address', 'location_link')
    list_filter = ('action', 'tenant')

    def location_link(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="https://www.google.com/maps?q={},{} " target="_blank">View on Map</a>',
                obj.latitude, obj.longitude
            )
        return "No GPS Data"

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'work_status', 'clock_in', 'clock_out', 'is_verified')
    list_editable = ('work_status', 'is_verified')
    actions = ['mark_as_verified']

    @admin.action(description="Verify selected attendance for payroll")
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)