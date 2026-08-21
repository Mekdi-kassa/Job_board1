from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import (
    get_company_dashboard,
    get_applicant_dashboard,
    get_admin_dashboard
)
from user.permissions import IsSuperAdmin


class CompanyDashboardView(APIView):
    """
    Company Hiring Dashboard with real-time pipeline funnel, job metrics, and recent applicants.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_company_dashboard(request.user)
        return Response({
            'success': True,
            'data': data
        }, status=status.HTTP_200_OK)


class ApplicantDashboardView(APIView):
    """
    Applicant Tracking Dashboard with hiring stages progress and skill-matched job recommendations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = get_applicant_dashboard(request.user)
        return Response({
            'success': True,
            'data': data
        }, status=status.HTTP_200_OK)


class AdminDashboardView(APIView):
    """
    Super Admin Platform Analytics with user growth, job health, and hiring conversion rate.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        data = get_admin_dashboard()
        return Response({
            'success': True,
            'data': data
        }, status=status.HTTP_200_OK)
