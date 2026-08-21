from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import FileExtensionValidator
from .validators import validate_safe_input, validate_rich_text, FileValidator
from django.conf import settings
import uuid
from datetime import timedelta
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        if extra_fields.get('username') == '':
            extra_fields['username'] = None
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        COMPANY = 'company', 'Company'
        APPLICANT = 'applicant', 'Applicant'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, validators=[validate_safe_input])
    last_name = models.CharField(max_length=100, validators=[validate_safe_input])
    username = models.CharField(max_length=30, unique=True, blank=True, null=True, validators=[validate_safe_input])
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.APPLICANT, db_index=True)
    
    # Applicant fields
    resume = models.FileField(
        upload_to='resumes/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx']), FileValidator.validate_file_type]
    )
    about_you = models.TextField(blank=True, validators=[validate_rich_text])
    
    # Company fields
    company_name = models.CharField(max_length=200, blank=True, null=True, validators=[validate_safe_input])
    company_logo = models.ImageField(
        upload_to='company_logos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']), FileValidator.validate_file_type]
    )
    company_description = models.TextField(blank=True, null=True, validators=[validate_rich_text])
    
    # Profile picture
    picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']), FileValidator.validate_file_type]
    )
    
    # Status flags
    is_active = models.BooleanField(default=False)  # ✅ Changed: False until email verified
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    
    # Email Verification Fields
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Password Reset Fields
    password_reset_token = models.CharField(max_length=255, blank=True, null=True)
    password_reset_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email', 'role']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['email_verification_token']),
            models.Index(fields=['password_reset_token']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name
    
    def is_company(self):
        return self.role == self.Role.COMPANY
    
    def is_applicant(self):
        return self.role == self.Role.APPLICANT
    
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN
    
    def is_email_verification_expired(self):
        """Check if email verification token has expired"""
        if not self.email_verification_sent_at:
            return True
        timeout_days = getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT_DAYS', 7)
        expiration_time = self.email_verification_sent_at + timedelta(days=timeout_days)
        return timezone.now() > expiration_time

    def is_password_reset_expired(self):
        """Check if password reset token has expired (1 hour limit)"""
        if not self.password_reset_sent_at:
            return True
        timeout_hours = getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 1)
        expiration_time = self.password_reset_sent_at + timedelta(hours=timeout_hours)
        return timezone.now() > expiration_time