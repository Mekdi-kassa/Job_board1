import bleach
from rest_framework import serializers
from .models import CompanyProfile, ApplicantProfile, Skill, WorkExperience, Education
from jobs.models import Job
from jobs.serializers import JobPublicListSerializer, CategorySerializer
from user.serializers import UserSerializer


class SkillSerializer(serializers.ModelSerializer):
    """Skill Serializer"""
    class Meta:
        model = Skill
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']

    def validate_name(self, value):
        import html
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if not cleaned:
            raise serializers.ValidationError("Skill name cannot be empty.")
        return cleaned


class WorkExperienceSerializer(serializers.ModelSerializer):
    """Work Experience Serializer"""
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'company_name', 'position', 'location',
            'start_date', 'end_date', 'is_current', 'description'
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        is_current = attrs.get('is_current', False)

        if not is_current and not end_date:
            raise serializers.ValidationError({"end_date": "Please specify an end date or mark as current role."})

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})

        return attrs


class EducationSerializer(serializers.ModelSerializer):
    """Education History Serializer"""
    class Meta:
        model = Education
        fields = [
            'id', 'institution', 'degree', 'field_of_study',
            'start_year', 'end_year', 'grade_or_gpa'
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        start_year = attrs.get('start_year')
        end_year = attrs.get('end_year')

        if start_year and (start_year < 1950 or start_year > 2100):
            raise serializers.ValidationError({"start_year": "Invalid start year."})

        if end_year and start_year and end_year < start_year:
            raise serializers.ValidationError({"end_year": "End year cannot be earlier than start year."})

        return attrs


class CompanyProfileSerializer(serializers.ModelSerializer):
    """Company Profile Management Serializer (for authenticated employer)"""
    email = serializers.EmailField(source='user.email', read_only=True)
    industry_detail = CategorySerializer(source='industry', read_only=True)
    active_jobs_count = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'email', 'company_name', 'slug', 'logo', 'tagline',
            'about', 'industry', 'industry_detail', 'company_size',
            'headquarters', 'website', 'linkedin_url', 'twitter_url',
            'github_url', 'is_verified_badge', 'active_jobs_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'is_verified_badge', 'created_at', 'updated_at']

    def get_active_jobs_count(self, obj):
        return Job.objects.filter(company=obj.user, status=Job.Status.PUBLISHED).count()

    def validate_company_name(self, value):
        import html
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if not cleaned:
            raise serializers.ValidationError("Company name cannot be empty.")
        return cleaned

    def validate_about(self, value):
        if value:
            return bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'br', 'strong', 'em', 'ul', 'ol', 'li'], strip=True)
        return ""


class CompanyPublicShowcaseSerializer(serializers.ModelSerializer):
    """Public Company Profile Showcase with Active Job Postings"""
    industry = CategorySerializer(read_only=True)
    active_jobs = serializers.SerializerMethodField()
    active_jobs_count = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'company_name', 'slug', 'logo', 'tagline', 'about',
            'industry', 'company_size', 'headquarters', 'website',
            'linkedin_url', 'twitter_url', 'github_url', 'is_verified_badge',
            'active_jobs_count', 'active_jobs'
        ]

    def get_active_jobs_count(self, obj):
        return Job.objects.filter(company=obj.user, status=Job.Status.PUBLISHED).count()

    def get_active_jobs(self, obj):
        active_jobs = Job.objects.filter(company=obj.user, status=Job.Status.PUBLISHED).order_by('-created_at')[:10]
        return JobPublicListSerializer(active_jobs, many=True).data


class ApplicantProfileSerializer(serializers.ModelSerializer):
    """Full Applicant Profile with Skills, Experiences, and Education"""
    user = UserSerializer(read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='skills'
    )
    experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicantProfile
        fields = [
            'id', 'user', 'headline', 'avatar', 'bio', 'location',
            'phone_number', 'resume', 'skills', 'skill_ids',
            'github_url', 'linkedin_url', 'portfolio_url',
            'is_open_to_work', 'preferred_job_type', 'preferred_workplace_type',
            'expected_salary', 'experiences', 'educations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_headline(self, value):
        import html
        return html.unescape(bleach.clean(value.strip(), tags=[], strip=True))

    def validate_bio(self, value):
        if value:
            return bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'br', 'strong', 'em'], strip=True)
        return ""


class TalentMarketplaceListSerializer(serializers.ModelSerializer):
    """Vetted Talent Card for Marketplace Directory"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    latest_experience = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantProfile
        fields = [
            'id', 'user_id', 'full_name', 'email', 'headline', 'avatar',
            'location', 'skills', 'is_open_to_work', 'preferred_job_type',
            'preferred_workplace_type', 'expected_salary', 'github_url',
            'linkedin_url', 'portfolio_url', 'latest_experience', 'updated_at'
        ]

    def get_latest_experience(self, obj):
        latest = obj.experiences.order_by('-start_date').first()
        if latest:
            return {
                'position': latest.position,
                'company_name': latest.company_name,
                'is_current': latest.is_current
            }
        return None
