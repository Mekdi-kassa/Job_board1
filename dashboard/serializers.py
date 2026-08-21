from rest_framework import serializers


class CompanyDashboardSerializer(serializers.Serializer):
    """Company hiring dashboard serializer"""
    overview = serializers.DictField()
    pipeline = serializers.DictField()
    top_jobs = serializers.ListField(child=serializers.DictField())
    recent_applicants = serializers.ListField(child=serializers.DictField())


class ApplicantDashboardSerializer(serializers.Serializer):
    """Applicant tracking dashboard serializer"""
    overview = serializers.DictField()
    recent_applications = serializers.ListField(child=serializers.DictField())
    recommended_jobs = serializers.ListField(child=serializers.DictField())


class AdminDashboardSerializer(serializers.Serializer):
    """Super Admin platform analytics serializer"""
    user_metrics = serializers.DictField()
    job_metrics = serializers.DictField()
    application_metrics = serializers.DictField()
    recent_activity = serializers.DictField()
