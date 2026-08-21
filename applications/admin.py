from django.contrib import admin
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant_email', 'job_title', 'company_name', 'status', 'rating', 'applied_at')
    list_filter = ('status', 'applied_at', 'rating')
    search_fields = ('applicant__email', 'applicant__first_name', 'applicant__last_name', 'job__title', 'job__company__email')
    readonly_fields = ('id', 'applied_at', 'updated_at', 'status_updated_at')
    ordering = ('-applied_at',)

    def applicant_email(self, obj):
        return obj.applicant.email
    applicant_email.short_description = 'Applicant'

    def job_title(self, obj):
        return obj.job.title
    job_title.short_description = 'Job'

    def company_name(self, obj):
        return obj.job.company.get_full_name() or obj.job.company.email
    company_name.short_description = 'Company'
