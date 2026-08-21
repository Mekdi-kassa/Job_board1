import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """In-App Notification and Email Alert Record"""

    class NotificationType(models.TextChoices):
        APPLICATION_STATUS_UPDATE = 'application_status_update', 'Application Status Update'
        NEW_APPLICANT = 'new_applicant', 'New Candidate Application'
        NEW_JOB_ALERT = 'new_job_alert', 'New Job Matching Alert'
        SYSTEM_ANNOUNCEMENT = 'system_announcement', 'System Announcement'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM_ANNOUNCEMENT
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Deep link to relevant application, job, or profile"
    )
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.email}: {self.title}"
