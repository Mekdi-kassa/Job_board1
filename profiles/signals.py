from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import CompanyProfile, ApplicantProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create appropriate profile when a User is created"""
    if created:
        if instance.role == 'company':
            CompanyProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'company_name': instance.get_full_name() or instance.username or "Company"
                }
            )
        elif instance.role == 'applicant':
            ApplicantProfile.objects.get_or_create(
                user=instance
            )
