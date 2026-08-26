import bleach
from rest_framework import serializers
from django.utils import timezone
from .models import Application
from jobs.models import Job
from jobs.serializers import JobPublicListSerializer, JobCompanySummarySerializer
from user.serializers import UserSerializer


class ApplicationSubmitSerializer(serializers.ModelSerializer):
    """Serializer for applicant submitting a job application"""
    cover_letter = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Application
        fields = ['id', 'resume', 'resume_url', 'cover_letter', 'status', 'applied_at']
        read_only_fields = ['id', 'status', 'applied_at']

    def validate_cover_letter(self, value):
        if value:
            import html
            return html.unescape(bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'br', 'strong', 'em', 'ul', 'ol', 'li'], strip=True))
        return ""

    def validate(self, attrs):
        resume = attrs.get('resume')
        resume_url = attrs.get('resume_url')
        job = self.context.get('job')
        user = self.context.get('request').user

        # 1. Require at least one resume source
        if not resume and not resume_url:
            raise serializers.ValidationError("You must upload a resume file or provide an external resume link.")

        # 2. Check job status and deadline
        if not job or job.status != Job.Status.PUBLISHED:
            raise serializers.ValidationError("This job is not currently accepting applications.")

        if job.deadline and job.deadline < timezone.now().date():
            raise serializers.ValidationError("The application deadline for this job has passed.")

        # 3. Check if user is applying to their own job
        if job.company == user:
            raise serializers.ValidationError("You cannot apply to your own job posting.")

        # 4. Check for duplicate application
        if Application.objects.filter(job=job, applicant=user).exists():
            raise serializers.ValidationError("You have already submitted an application for this job.")

        return attrs

    def create(self, validated_data):
        job = self.context.get('job')
        user = self.context.get('request').user
        validated_data['job'] = job
        validated_data['applicant'] = user
        return super().create(validated_data)


class ApplicantApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for applicant viewing their submitted applications"""
    job = JobPublicListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'job', 'resume', 'resume_url', 'cover_letter',
            'status', 'status_display', 'applied_at', 'status_updated_at'
        ]


class CompanyCandidateApplicationSerializer(serializers.ModelSerializer):
    """Serializer for employers reviewing applicants"""
    applicant = UserSerializer(read_only=True)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    applicant_email = serializers.EmailField(source='applicant.email', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'applicant', 'applicant_name', 'applicant_email',
            'profile', 'resume', 'resume_url', 'cover_letter', 'status',
            'status_display', 'rating', 'company_notes', 'applied_at', 'status_updated_at'
        ]

    def get_profile(self, obj):
        try:
            from profiles.models import ApplicantProfile
            from profiles.serializers import ApplicantProfileSerializer
            profile = ApplicantProfile.objects.select_related('user').prefetch_related('skills', 'experiences', 'educations').get(user=obj.applicant)
            return ApplicantProfileSerializer(profile, context=self.context).data
        except Exception:
            return None


class CompanyStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for company updating candidate status & review notes"""
    class Meta:
        model = Application
        fields = ['status', 'rating', 'company_notes']

    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be an integer between 1 and 5.")
        return value

    def validate_company_notes(self, value):
        if value:
            import html
            return html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        return ""
