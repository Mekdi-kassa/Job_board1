import uuid
from django.db import models
from django.conf import settings


class Report(models.Model):
    """Platform Report against a Job, Company, or User"""

    class TargetType(models.TextChoices):
        JOB = 'job', 'Job Posting'
        USER = 'user', 'User / Company Account'

    class Reason(models.TextChoices):
        SPAM_OR_SCAM = 'spam_or_scam', 'Spam, Fraud, or Scam'
        FAKE_JOB = 'fake_job', 'Fake or Misleading Job'
        INAPPROPRIATE_CONTENT = 'inappropriate_content', 'Inappropriate or Offensive Content'
        HARASSMENT = 'harassment', 'Harassment or Threatening Behavior'
        DISCRIMINATION = 'discrimination', 'Discriminatory Language or Practice'
        IMPERSONATION = 'impersonation', 'Impersonation or False Identity'
        OTHER = 'other', 'Other Issue'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        UNDER_REVIEW = 'under_review', 'Under Investigation'
        ACTION_TAKEN = 'action_taken', 'Action Taken'
        DISMISSED = 'dismissed', 'Dismissed / No Violation'

    class ActionTaken(models.TextChoices):
        NONE = 'none', 'No Action Yet'
        JOB_REMOVED = 'job_removed', 'Job Removed / Closed'
        USER_WARNED = 'user_warned', 'User Warned'
        USER_SUSPENDED = 'user_suspended', 'User Account Suspended'
        DISMISSED = 'dismissed', 'Report Dismissed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_reports'
    )
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.JOB
    )
    reported_job = models.ForeignKey(
        'jobs.Job',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports'
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='received_reports'
    )
    reason = models.CharField(
        max_length=40,
        choices=Reason.choices,
        default=Reason.SPAM_OR_SCAM
    )
    description = models.TextField(help_text="Detailed explanation of the issue")
    evidence_url = models.URLField(
        blank=True,
        default="",
        help_text="Optional link to screenshot, document, or external evidence"
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )
    action_taken = models.CharField(
        max_length=30,
        choices=ActionTaken.choices,
        default=ActionTaken.NONE
    )
    admin_notes = models.TextField(
        blank=True,
        default="",
        help_text="Super Admin resolution investigation notes"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['target_type', 'status']),
            models.Index(fields=['reporter', '-created_at']),
        ]

    def __str__(self):
        return f"Report {self.id} by {self.reporter.email} ({self.status})"
