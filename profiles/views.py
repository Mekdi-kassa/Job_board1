import uuid
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import CompanyProfile, ApplicantProfile, Skill, WorkExperience, Education
from .serializers import (
    CompanyProfileSerializer,
    CompanyPublicShowcaseSerializer,
    ApplicantProfileSerializer,
    SkillSerializer,
    WorkExperienceSerializer,
    EducationSerializer
)
from .permissions import IsExperienceOwner, IsEducationOwner
from jobs.views import StandardResultsSetPagination


# ============================================================
# COMPANY PROFILE VIEWS
# ============================================================

class CompanyMyProfileView(APIView):
    """
    Get or update authenticated company's own profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = CompanyProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'company_name': self.request.user.get_full_name() or self.request.user.username or "Company"
            }
        )
        return profile

    def get(self, request):
        profile = self.get_object()
        serializer = CompanyProfileSerializer(profile)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request):
        profile = self.get_object()
        serializer = CompanyProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Company profile updated successfully.',
                'data': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        return self.patch(request)


class CompanyLogoUploadView(APIView):
    """
    Upload company brand logo.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
        logo_file = request.FILES.get('logo')

        if not logo_file:
            return Response({
                'success': False,
                'message': 'No logo file provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile.logo = logo_file
        profile.save(update_fields=['logo', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Logo uploaded successfully.',
            'logo_url': profile.logo.url if profile.logo else None
        })


class CompanyPublicListView(generics.ListAPIView):
    """
    Public directory of companies.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CompanyPublicShowcaseSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = CompanyProfile.objects.select_related('industry', 'user').all()
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(tagline__icontains=q) |
                Q(about__icontains=q) |
                Q(headquarters__icontains=q)
            )
        industry_slug = self.request.query_params.get('industry')
        if industry_slug:
            queryset = queryset.filter(industry__slug=industry_slug)

        return queryset.order_by('company_name')


class CompanyPublicShowcaseDetailView(APIView):
    """
    Public company showcase with active job listings.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug_or_id):
        # Look up by slug or UUID
        try:
            val_uuid = uuid.UUID(str(slug_or_id))
            profile = get_object_or_404(
                CompanyProfile.objects.select_related('industry', 'user'),
                Q(pk=val_uuid) | Q(slug=slug_or_id)
            )
        except ValueError:
            profile = get_object_or_404(
                CompanyProfile.objects.select_related('industry', 'user'),
                slug=slug_or_id
            )

        serializer = CompanyPublicShowcaseSerializer(profile)
        return Response({
            'success': True,
            'data': serializer.data
        })


# ============================================================
# APPLICANT PROFILE VIEWS
# ============================================================

class ApplicantMyProfileView(APIView):
    """
    Get or update authenticated applicant's own profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get(self, request):
        profile = self.get_object()
        serializer = ApplicantProfileSerializer(profile)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request):
        profile = self.get_object()
        serializer = ApplicantProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Applicant profile updated successfully.',
                'data': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        return self.patch(request)


class ApplicantAvatarUploadView(APIView):
    """
    Upload applicant profile avatar / photo.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = ApplicantProfile.objects.get_or_create(user=request.user)
        avatar_file = request.FILES.get('avatar')

        if not avatar_file:
            return Response({
                'success': False,
                'message': 'No avatar file provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile.avatar = avatar_file
        profile.save(update_fields=['avatar', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Avatar uploaded successfully.',
            'avatar_url': profile.avatar.url if profile.avatar else None
        })


# ============================================================
# SKILLS & EXPERIENCE & EDUCATION VIEWS
# ============================================================

class SkillListCreateView(generics.ListCreateAPIView):
    """
    List or create skills.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = SkillSerializer
    queryset = Skill.objects.all()
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Skill.objects.all()
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset


class ApplicantWorkExperienceListCreateView(generics.ListCreateAPIView):
    """
    List or add work experience to applicant profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkExperienceSerializer

    def get_queryset(self):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        return WorkExperience.objects.filter(profile=profile)

    def perform_create(self, serializer):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class ApplicantWorkExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage single work experience entry.
    """
    permission_classes = [permissions.IsAuthenticated, IsExperienceOwner]
    serializer_class = WorkExperienceSerializer
    queryset = WorkExperience.objects.all()


class ApplicantEducationListCreateView(generics.ListCreateAPIView):
    """
    List or add education to applicant profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EducationSerializer

    def get_queryset(self):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        return Education.objects.filter(profile=profile)

    def perform_create(self, serializer):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class ApplicantEducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage single education entry.
    """
    permission_classes = [permissions.IsAuthenticated, IsEducationOwner]
    serializer_class = EducationSerializer
    queryset = Education.objects.all()
