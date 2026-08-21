import html
import bleach
from rest_framework import serializers
from django.shortcuts import get_object_or_404

from .models import Report
from user.models import User
from jobs.models import Job


class ReportSubmitSerializer(serializers.ModelSerializer):
    """Serializer for submitting a report"""
    job_id = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    user_id = serializers.UUIDField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = Report
        fields = [
            'id', 'target_type', 'job_id', 'user_id',
            'reason', 'description', 'evidence_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_description(self, value):
        cleaned = html.unescape(bleach.clean(value.strip(), tags=[], strip=True))
        if len(cleaned) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long.")
        return cleaned

    def validate(self, attrs):
        target_type = attrs.get('target_type')
        job_id = attrs.get('job_id')
        user_id = attrs.get('user_id')
        user = self.context['request'].user

        if target_type == Report.TargetType.JOB:
            if not job_id:
                raise serializers.ValidationError({"job_id": "job_id is required when reporting a job."})
            try:
                job = Job.objects.get(id=job_id)
                attrs['reported_job'] = job
            except Job.DoesNotExist:
                raise serializers.ValidationError({"job_id": "Specified job does not exist."})

        elif target_type == Report.TargetType.USER:
            if not user_id:
                raise serializers.ValidationError({"user_id": "user_id is required when reporting a user/company."})
            try:
                reported_u = User.objects.get(id=user_id)
                if reported_u == user:
                    raise serializers.ValidationError({"user_id": "You cannot report your own account."})
                attrs['reported_user'] = reported_u
            except User.DoesNotExist:
                raise serializers.ValidationError({"user_id": "Specified user does not exist."})
        else:
            raise serializers.ValidationError({"target_type": "Invalid target type."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('job_id', None)
        validated_data.pop('user_id', None)
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)


class ReporterReportListSerializer(serializers.ModelSerializer):
    """Serializer for user viewing their own submitted reports"""
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    action_taken_display = serializers.CharField(source='get_action_taken_display', read_only=True)
    target_summary = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'target_type', 'target_summary', 'reason', 'reason_display',
            'description', 'evidence_url', 'status', 'status_display',
            'action_taken_display', 'admin_notes', 'created_at', 'resolved_at'
        ]

    def get_target_summary(self, obj):
        if obj.target_type == Report.TargetType.JOB and obj.reported_job:
            return {
                'id': str(obj.reported_job.id),
                'title': obj.reported_job.title,
                'company': obj.reported_job.company.get_full_name() or obj.reported_job.company.username
            }
        elif obj.target_type == Report.TargetType.USER and obj.reported_user:
            return {
                'id': str(obj.reported_user.id),
                'name': obj.reported_user.get_full_name() or obj.reported_user.username,
                'email': obj.reported_user.email,
                'role': obj.reported_user.role
            }
        return None


class AdminReportDetailSerializer(serializers.ModelSerializer):
    """Full detail report for Super Admin moderation"""
    reporter_info = serializers.SerializerMethodField()
    target_info = serializers.SerializerMethodField()
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    action_taken_display = serializers.CharField(source='get_action_taken_display', read_only=True)
    resolved_by_email = serializers.EmailField(source='resolved_by.email', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'reporter_info', 'target_type', 'target_info', 'reason',
            'reason_display', 'description', 'evidence_url', 'status',
            'status_display', 'action_taken', 'action_taken_display',
            'admin_notes', 'resolved_by_email', 'created_at', 'resolved_at'
        ]

    def get_reporter_info(self, obj):
        return {
            'id': str(obj.reporter.id),
            'email': obj.reporter.email,
            'name': obj.reporter.get_full_name() or obj.reporter.username,
            'role': obj.reporter.role
        }

    def get_target_info(self, obj):
        if obj.target_type == Report.TargetType.JOB and obj.reported_job:
            return {
                'type': 'job',
                'id': str(obj.reported_job.id),
                'title': obj.reported_job.title,
                'status': obj.reported_job.status,
                'company_email': obj.reported_job.company.email,
                'company_name': obj.reported_job.company.get_full_name() or obj.reported_job.company.username
            }
        elif obj.target_type == Report.TargetType.USER and obj.reported_user:
            return {
                'type': 'user',
                'id': str(obj.reported_user.id),
                'email': obj.reported_user.email,
                'name': obj.reported_user.get_full_name() or obj.reported_user.username,
                'role': obj.reported_user.role,
                'is_verified': obj.reported_user.is_verified,
                'is_suspended': obj.reported_user.is_suspended
            }
        return None


class AdminReportResolveSerializer(serializers.Serializer):
    """Serializer for Super Admin resolving a report"""
    status = serializers.ChoiceField(choices=Report.Status.choices)
    action_taken = serializers.ChoiceField(choices=Report.ActionTaken.choices)
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")
