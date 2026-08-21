from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Application
from .serializers import (
    ApplicationSubmitSerializer,
    ApplicantApplicationListSerializer,
    CompanyCandidateApplicationSerializer,
    CompanyStatusUpdateSerializer,
)
from .permissions import IsApplicationOwner, IsApplicationJobOwner
from .utils import (
    send_application_submitted_email,
    send_company_new_applicant_email,
    send_application_status_update_email,
)
from jobs.models import Job
from jobs.views import StandardResultsSetPagination
from user.permissions import IsSuperAdmin


# ============================================================
# APPLICANT ENDPOINTS
# ============================================================

class JobApplyView(APIView):
    """
    Submit a Job Application with Resume File and optional Cover Letter.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)

        serializer = ApplicationSubmitSerializer(
            data=request.data,
            context={'request': request, 'job': job}
        )

        if serializer.is_valid():
            application = serializer.save()

            # Trigger automated emails asynchronously/safely
            try:
                send_application_submitted_email(application)
                send_company_new_applicant_email(application)
            except Exception as e:
                print(f"Error triggering application emails: {e}")

            return Response({
                'success': True,
                'message': 'Application submitted successfully.',
                'data': ApplicantApplicationListSerializer(application).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ApplicantMyApplicationsListView(generics.ListAPIView):
    """
    List all job applications submitted by the logged-in applicant.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ApplicantApplicationListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Application.objects.filter(
            applicant=self.request.user
        ).select_related('job', 'job__company', 'job__category')
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by('-applied_at')


class ApplicantApplicationDetailView(APIView):
    """
    Retrieve single application detail submitted by applicant.
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationOwner]

    def get(self, request, pk):
        application = get_object_or_404(
            Application.objects.select_related('job', 'job__company', 'job__category'),
            pk=pk
        )
        self.check_object_permissions(request, application)
        serializer = ApplicantApplicationListSerializer(application)
        return Response({
            'success': True,
            'data': serializer.data
        })


class ApplicantApplicationWithdrawView(APIView):
    """
    Withdraw a previously submitted application.
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationOwner]

    def post(self, request, pk):
        application = get_object_or_404(Application, pk=pk)
        self.check_object_permissions(request, application)

        if application.status in (Application.Status.HIRED, Application.Status.REJECTED):
            return Response({
                'success': False,
                'message': f"Cannot withdraw an application that has already been {application.status}."
            }, status=status.HTTP_400_BAD_REQUEST)

        application.status = Application.Status.WITHDRAWN
        application.status_updated_at = timezone.now()
        application.save(update_fields=['status', 'status_updated_at', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Application has been withdrawn successfully.',
            'data': {
                'id': str(application.id),
                'status': application.status
            }
        }, status=status.HTTP_200_OK)


# ============================================================
# COMPANY REVIEW & HIRING PIPELINE ENDPOINTS
# ============================================================

class CompanyJobApplicationsListView(generics.ListAPIView):
    """
    List all candidates who applied for a specific job owned by the company.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyCandidateApplicationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, pk=job_id)

        # Ensure user owns this job (or is admin)
        if not (self.request.user.is_superuser or self.request.user.role == 'super_admin' or job.company == self.request.user):
            return Application.objects.none()

        queryset = Application.objects.filter(job=job).select_related('applicant', 'job')
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        rating_param = self.request.query_params.get('min_rating')
        if rating_param:
            try:
                queryset = queryset.filter(rating__gte=int(rating_param))
            except ValueError:
                pass

        return queryset.order_by('-applied_at')


class CompanyAllApplicationsListView(generics.ListAPIView):
    """
    List all candidates across all jobs posted by the company.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyCandidateApplicationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Application.objects.filter(
            job__company=self.request.user
        ).select_related('applicant', 'job')

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset.order_by('-applied_at')


class CompanyApplicationDetailReviewView(APIView):
    """
    Get full candidate details or Update candidate status, rating, and reviewer notes.
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationJobOwner]

    def get_object(self, pk):
        app = get_object_or_404(Application.objects.select_related('applicant', 'job', 'job__company'), pk=pk)
        self.check_object_permissions(self.request, app)
        return app

    def get(self, request, pk):
        application = self.get_object(pk)
        serializer = CompanyCandidateApplicationSerializer(application)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request, pk):
        application = self.get_object(pk)
        old_status = application.status

        serializer = CompanyStatusUpdateSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            updated_app = serializer.save()
            new_status = updated_app.status

            # If status changed, update timestamp and send email notification
            if new_status != old_status:
                updated_app.status_updated_at = timezone.now()
                updated_app.save(update_fields=['status_updated_at'])

                try:
                    send_application_status_update_email(updated_app)
                except Exception as e:
                    print(f"Error sending status update email: {e}")

            return Response({
                'success': True,
                'message': f"Application status updated to '{updated_app.get_status_display()}'.",
                'data': CompanyCandidateApplicationSerializer(updated_app).data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# SUPER ADMIN MODERATION
# ============================================================

class AdminApplicationListView(generics.ListAPIView):
    """
    Super Admin view of all applications across all jobs.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = CompanyCandidateApplicationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Application.objects.all().select_related('applicant', 'job', 'job__company')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by('-applied_at')
