from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter_email', 'target_type', 'reason', 'status', 'action_taken', 'created_at')
    list_filter = ('target_type', 'reason', 'status', 'action_taken', 'created_at')
    search_fields = ('reporter__email', 'reported_job__title', 'reported_user__email', 'description', 'admin_notes')
    readonly_fields = ('id', 'created_at', 'resolved_at')

    def reporter_email(self, obj):
        return obj.reporter.email
    reporter_email.short_description = 'Reporter'
