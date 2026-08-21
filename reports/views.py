from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Report
from .serializers import (
    ReportSubmitSerializer,
    ReporterReportListSerializer,
    AdminReportDetailSerializer,
    AdminReportResolveSerializer
)
from .permissions import IsReportReporter
from user.permissions import IsSuperAdmin
from jobs.models import Job
from jobs.views import StandardResultsSetPagination
from notifications.services import create_and_send_notification
from notifications.models import Notification


class ReportSubmitView(generics.CreateAPIView):
    """
    Submit a report against a job posting or user/company account.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportSubmitSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            report = serializer.save()
            return Response({
                'success': True,
                'message': 'Report submitted successfully. Our moderation team will investigate.',
                'data': ReporterReportListSerializer(report).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class MyReportsListView(generics.ListAPIView):
    """
    List reports submitted by the logged-in user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReporterReportListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user).select_related(
            'reported_job', 'reported_job__company', 'reported_user'
        )


class MyReportDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a single report submitted by the logged-in user.
    """
    permission_classes = [permissions.IsAuthenticated, IsReportReporter]
    serializer_class = ReporterReportListSerializer
    queryset = Report.objects.all().select_related(
        'reported_job', 'reported_job__company', 'reported_user'
    )


class AdminReportListView(generics.ListAPIView):
    """
    Super Admin: List all platform reports with status and target_type filters.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = AdminReportDetailSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Report.objects.all().select_related(
            'reporter', 'reported_job', 'reported_job__company', 'reported_user', 'resolved_by'
        )
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        target_type_param = self.request.query_params.get('target_type')
        if target_type_param:
            queryset = queryset.filter(target_type=target_type_param)

        reason_param = self.request.query_params.get('reason')
        if reason_param:
            queryset = queryset.filter(reason=reason_param)

        return queryset


class AdminReportDetailView(generics.RetrieveAPIView):
    """
    Super Admin: Inspect full report details, reporter info, and target evidence.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = AdminReportDetailSerializer
    queryset = Report.objects.all().select_related(
        'reporter', 'reported_job', 'reported_job__company', 'reported_user', 'resolved_by'
    )


class AdminReportResolveView(APIView):
    """
    Super Admin: Resolve report and trigger automatic moderation actions:
    - job_removed: Closes job posting
    - user_suspended: Suspends reported user account
    - dismissed: Closes investigation with no action
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        report = get_object_or_404(
            Report.objects.select_related('reporter', 'reported_job', 'reported_user'),
            pk=pk
        )
        serializer = AdminReportResolveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        action_taken = serializer.validated_data['action_taken']
        admin_notes = serializer.validated_data.get('admin_notes', '')

        report.status = new_status
        report.action_taken = action_taken
        report.admin_notes = admin_notes
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        # Execute Moderation Action
        if action_taken == Report.ActionTaken.JOB_REMOVED and report.reported_job:
            report.reported_job.status = Job.Status.CLOSED
            report.reported_job.is_featured = False
            report.reported_job.save(update_fields=['status', 'is_featured'])

        elif action_taken == Report.ActionTaken.USER_SUSPENDED and report.reported_user:
            report.reported_user.is_suspended = True
            report.reported_user.save(update_fields=['is_suspended'])

        # Notify Reporter that report was resolved
        try:
            create_and_send_notification(
                recipient=report.reporter,
                sender=request.user,
                notification_type=Notification.NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Update on your submitted report",
                message=f"Your report ({report.get_reason_display()}) has been reviewed and marked as '{report.get_status_display()}'. Thank you for keeping our community safe.",
                action_url=f"/api/reports/my-reports/{report.id}/",
                send_email=True
            )
        except Exception as e:
            print(f"Error notifying reporter: {e}")

        return Response({
            'success': True,
            'message': f"Report resolved successfully with action '{report.get_action_taken_display()}'.",
            'data': AdminReportDetailSerializer(report).data
        }, status=status.HTTP_200_OK)
