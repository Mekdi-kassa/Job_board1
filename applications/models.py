import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_resume_file(file):
    """Validate file extension and size (Max 5MB)"""
    import os
    ext = os.path.splitext(file.name)[1].lower()
    valid_extensions = ['.pdf', '.doc', '.docx', '.rtf']
    if ext not in valid_extensions:
        raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats are: {', '.join(valid_extensions)}")
    
    # 5MB limit
    max_size = 5 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError("Resume file size cannot exceed 5MB.")


class Application(models.Model):
    """Job Application Model"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        REVIEWED = 'reviewed', 'Reviewed'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        INTERVIEWED = 'interviewed', 'Interview Scheduled / Interviewed'
        OFFERED = 'offered', 'Offer Extended'
        HIRED = 'hired', 'Hired'
        REJECTED = 'rejected', 'Not Selected'
        WITHDRAWN = 'withdrawn', 'Withdrawn by Applicant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    
    # Documents & Notes
    resume = models.FileField(
        upload_to='resumes/%Y/%m/',
        validators=[validate_resume_file],
        blank=True,
        null=True
    )
    resume_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Optional external link to resume or portfolio (e.g. Google Drive, LinkedIn)"
    )
    cover_letter = models.TextField(
        blank=True,
        default="",
        help_text="Cover letter or note to the employer"
    )
    
    # Hiring Pipeline & Review
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    company_notes = models.TextField(
        blank=True,
        default="",
        help_text="Private internal notes for the hiring team"
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Candidate evaluation score (1-5)"
    )
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status_updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'job_applications'
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='unique_job_application'
            )
        ]
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['applicant', '-applied_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.applicant.get_full_name()} applied to {self.job.title}"

    def clean(self):
        if not self.resume and not self.resume_url:
            raise ValidationError("Please provide a resume file or a resume link.")
        if self.rating and (self.rating < 1 or self.rating > 5):
            raise ValidationError("Rating must be between 1 and 5.")

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            # Atomically increment job application count
            from jobs.models import Job
            Job.objects.filter(pk=self.job_id).update(applications_count=models.F('applications_count') + 1)
