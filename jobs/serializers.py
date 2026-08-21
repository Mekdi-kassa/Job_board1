import bleach
from rest_framework import serializers
from django.utils import timezone
from .models import Category, Job
from user.models import User


class CategorySerializer(serializers.ModelSerializer):
    job_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'is_active', 'job_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def validate_name(self, value):
        import html
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if not cleaned:
            raise serializers.ValidationError("Category name cannot be empty.")
        return cleaned


class JobCompanySummarySerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'company_name', 'first_name', 'last_name']

    def get_company_name(self, obj):
        return obj.get_full_name() or obj.username or obj.email


class JobPublicListSerializer(serializers.ModelSerializer):
    company = JobCompanySummarySerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'slug', 'title', 'company', 'category',
            'job_type', 'workplace_type', 'location', 'experience_level',
            'min_salary', 'max_salary', 'salary_currency', 'salary_is_negotiable',
            'is_salary_visible', 'status', 'is_featured', 'deadline',
            'views_count', 'applications_count', 'is_active', 'created_at'
        ]


class JobDetailSerializer(serializers.ModelSerializer):
    company = JobCompanySummarySerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'slug', 'title', 'company', 'category',
            'description', 'requirements', 'responsibilities',
            'job_type', 'workplace_type', 'location', 'experience_level',
            'min_salary', 'max_salary', 'salary_currency', 'salary_is_negotiable',
            'is_salary_visible', 'status', 'is_featured', 'deadline',
            'views_count', 'applications_count', 'is_active',
            'created_at', 'updated_at'
        ]


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source='category',
        write_only=True
    )
    category = CategorySerializer(read_only=True)
    company = JobCompanySummarySerializer(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'slug', 'title', 'company', 'category', 'category_id',
            'description', 'requirements', 'responsibilities',
            'job_type', 'workplace_type', 'location', 'experience_level',
            'min_salary', 'max_salary', 'salary_currency', 'salary_is_negotiable',
            'is_salary_visible', 'status', 'is_featured', 'deadline',
            'views_count', 'applications_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'company', 'views_count', 'applications_count', 'is_featured', 'created_at', 'updated_at']

    def validate_title(self, value):
        import html
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if len(cleaned) < 3:
            raise serializers.ValidationError("Job title must be at least 3 characters long.")
        return cleaned

    def validate_description(self, value):
        cleaned = bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'h3', 'h4'], strip=True)
        if len(cleaned) < 10:
            raise serializers.ValidationError("Job description must be at least 10 characters long.")
        return cleaned

    def validate_requirements(self, value):
        cleaned = bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'h3', 'h4'], strip=True)
        if len(cleaned) < 10:
            raise serializers.ValidationError("Job requirements must be at least 10 characters long.")
        return cleaned

    def validate_responsibilities(self, value):
        if value:
            return bleach.clean(value.strip(), tags=['p', 'b', 'i', 'u', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'h3', 'h4'], strip=True)
        return ""

    def validate_location(self, value):
        import html
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if not cleaned:
            raise serializers.ValidationError("Location cannot be empty.")
        return cleaned

    def validate_deadline(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Application deadline cannot be in the past.")
        return value

    def validate(self, attrs):
        min_salary = attrs.get('min_salary')
        max_salary = attrs.get('max_salary')

        # If partial update, check instance
        if self.instance:
            if min_salary is None:
                min_salary = self.instance.min_salary
            if max_salary is None:
                max_salary = self.instance.max_salary

        if min_salary is not None and max_salary is not None:
            if min_salary > max_salary:
                raise serializers.ValidationError({
                    "max_salary": "Maximum salary cannot be less than minimum salary."
                })

        return attrs

    def create(self, validated_data):
        # Automatically associate with requesting company user
        request = self.context.get('request')
        validated_data['company'] = request.user
        return super().create(validated_data)
