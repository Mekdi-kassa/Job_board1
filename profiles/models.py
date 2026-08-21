import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Skill(models.Model):
    """Candidate Technical & Soft Skills"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        db_table = 'skills'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CompanyProfile(models.Model):
    """Company Profile Showcase & Branding"""

    class CompanySize(models.TextChoices):
        SIZE_1_10 = '1-10', '1-10 Employees (Startup)'
        SIZE_11_50 = '11-50', '11-50 Employees (Small)'
        SIZE_51_200 = '51-200', '51-200 Employees (Medium)'
        SIZE_201_500 = '201-500', '201-500 Employees (Large)'
        SIZE_500_PLUS = '500+', '500+ Employees (Enterprise)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    company_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    logo = models.ImageField(upload_to='company_logos/%Y/%m/', blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True, default="")
    about = models.TextField(blank=True, default="")
    industry = models.ForeignKey(
        'jobs.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='companies'
    )
    company_size = models.CharField(
        max_length=20,
        choices=CompanySize.choices,
        default=CompanySize.SIZE_11_50
    )
    headquarters = models.CharField(max_length=200, blank=True, default="")
    website = models.URLField(max_length=300, blank=True, default="")
    linkedin_url = models.URLField(max_length=300, blank=True, default="")
    twitter_url = models.URLField(max_length=300, blank=True, default="")
    github_url = models.URLField(max_length=300, blank=True, default="")
    is_verified_badge = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'company_profiles'
        ordering = ['company_name']

    def __str__(self):
        return self.company_name or f"Company Profile ({self.user.email})"

    def save(self, *args, **kwargs):
        if not self.company_name:
            self.company_name = self.user.get_full_name() or self.user.username or "Company"
        if not self.slug:
            base_slug = slugify(self.company_name) or "company"
            candidate_slug = base_slug
            counter = 1
            while CompanyProfile.objects.filter(slug=candidate_slug).exclude(pk=self.pk).exists():
                candidate_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate_slug
        super().save(*args, **kwargs)


class ApplicantProfile(models.Model):
    """Job Seeker / Applicant Profile with Resume, Skills, and Preferences"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applicant_profile'
    )
    headline = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="e.g. Senior Full Stack Engineer | Python, React, AWS"
    )
    avatar = models.ImageField(upload_to='applicant_avatars/%Y/%m/', blank=True, null=True)
    bio = models.TextField(blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    phone_number = models.CharField(max_length=30, blank=True, default="")
    resume = models.FileField(upload_to='applicant_resumes/%Y/%m/', blank=True, null=True)
    
    skills = models.ManyToManyField(Skill, related_name='applicants', blank=True)
    
    # Portfolio and Social links
    github_url = models.URLField(max_length=300, blank=True, default="")
    linkedin_url = models.URLField(max_length=300, blank=True, default="")
    portfolio_url = models.URLField(max_length=300, blank=True, default="")
    
    # Career Preferences
    is_open_to_work = models.BooleanField(default=True)
    preferred_job_type = models.CharField(max_length=30, blank=True, default="")
    preferred_workplace_type = models.CharField(max_length=30, blank=True, default="")
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'applicant_profiles'

    def __str__(self):
        return f"Applicant Profile: {self.user.get_full_name()} ({self.user.email})"


class WorkExperience(models.Model):
    """Applicant Work Experience Entry"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ApplicantProfile,
        on_delete=models.CASCADE,
        related_name='experiences'
    )
    company_name = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True, default="")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = 'work_experiences'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.position} at {self.company_name}"


class Education(models.Model):
    """Applicant Education History Entry"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ApplicantProfile,
        on_delete=models.CASCADE,
        related_name='educations'
    )
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(null=True, blank=True)
    grade_or_gpa = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = 'education_entries'
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.degree} in {self.field_of_study} from {self.institution}"
