from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient_email', 'notification_type', 'title', 'is_read', 'email_sent', 'created_at')
    list_filter = ('notification_type', 'is_read', 'email_sent', 'created_at')
    search_fields = ('recipient__email', 'title', 'message')
    readonly_fields = ('id', 'created_at')

    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = 'Recipient'
