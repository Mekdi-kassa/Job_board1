import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone


class Category(models.Model):
    """Job Category Model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="briefcase", help_text="Icon identifier e.g. code, chart-bar, heart")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Job(models.Model):
    """Job Posting Model"""

    class JobType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        CONTRACT = 'contract', 'Contract'
        INTERNSHIP = 'internship', 'Internship'
        FREELANCE = 'freelance', 'Freelance'
        TEMPORARY = 'temporary', 'Temporary'

    class WorkplaceType(models.TextChoices):
        ON_SITE = 'on_site', 'On-site'
        REMOTE = 'remote', 'Remote'
        HYBRID = 'hybrid', 'Hybrid'

    class ExperienceLevel(models.TextChoices):
        ENTRY = 'entry', 'Entry Level'
        JUNIOR = 'junior', 'Junior'
        MID = 'mid', 'Mid Level'
        SENIOR = 'senior', 'Senior'
        LEAD = 'lead', 'Lead / Manager'
        EXECUTIVE = 'executive', 'Executive'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'
        ARCHIVED = 'archived', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='jobs'
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField(help_text="Detailed job description and summary")
    requirements = models.TextField(help_text="Skills, qualifications, and requirements")
    responsibilities = models.TextField(blank=True, default="", help_text="Day-to-day responsibilities")
    
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    workplace_type = models.CharField(max_length=20, choices=WorkplaceType.choices, default=WorkplaceType.ON_SITE)
    location = models.CharField(max_length=150, help_text="City, State, Country or 'Remote'")
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices, default=ExperienceLevel.MID)
    
    # Compensation
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD')
    salary_is_negotiable = models.BooleanField(default=False)
    is_salary_visible = models.BooleanField(default=True)
    
    # State & Visibility
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    is_featured = models.BooleanField(default=False)
    deadline = models.DateField(null=True, blank=True)
    
    # Stats
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['job_type']),
            models.Index(fields=['workplace_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['location']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.title} - {self.company.get_full_name() or self.company.email}"

    @property
    def is_active(self):
        """Check if job is active and not passed deadline"""
        if self.status != self.Status.PUBLISHED:
            return False
        if self.deadline and self.deadline < timezone.now().date():
            return False
        return True

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            uid_short = uuid.uuid4().hex[:6]
            slug = f"{base_slug}-{uid_short}" if base_slug else uid_short
            self.slug = slug
        super().save(*args, **kwargs)

    def increment_views(self):
        """Atomically increment views count"""
        Job.objects.filter(pk=self.pk).update(views_count=models.F('views_count') + 1)
        self.refresh_from_db(fields=['views_count'])
