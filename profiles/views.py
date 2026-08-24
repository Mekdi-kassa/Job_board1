import uuid
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import CompanyProfile, ApplicantProfile, Skill, WorkExperience, Education
from jobs.models import Job
from .serializers import (
    CompanyProfileSerializer,
    CompanyPublicShowcaseSerializer,
    ApplicantProfileSerializer,
    TalentMarketplaceListSerializer,
    SkillSerializer,
    WorkExperienceSerializer,
    EducationSerializer
)
from .permissions import IsExperienceOwner, IsEducationOwner
from user.permissions import IsSuperAdmin
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


class ApplicantResumeUploadView(APIView):
    """
    Upload applicant resume document (PDF, DOCX).
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = ApplicantProfile.objects.get_or_create(user=request.user)
        resume_file = request.FILES.get('resume')

        if not resume_file:
            return Response({
                'success': False,
                'message': 'No resume file provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile.resume = resume_file
        profile.save(update_fields=['resume', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Resume uploaded successfully.',
            'resume_url': profile.resume.url if profile.resume else None
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


# ============================================================
# TALENT & COMMUNITY MARKETPLACE VIEWS
# ============================================================

class TalentMarketplaceListView(generics.ListAPIView):
    """
    Authenticated Directory of verified candidates and talent.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TalentMarketplaceListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = ApplicantProfile.objects.select_related('user').prefetch_related('skills', 'experiences').filter(
            user__is_active=True,
            is_open_to_work=True
        )

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(headline__icontains=q) |
                Q(bio__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(skills__name__icontains=q)
            ).distinct()

        skill = self.request.query_params.get('skill')
        if skill:
            queryset = queryset.filter(
                Q(skills__name__iexact=skill) | Q(skills__slug__iexact=skill)
            ).distinct()

        job_type = self.request.query_params.get('job_type')
        if job_type:
            queryset = queryset.filter(preferred_job_type__iexact=job_type)

        workplace_type = self.request.query_params.get('workplace_type')
        if workplace_type:
            queryset = queryset.filter(preferred_workplace_type__iexact=workplace_type)

        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        return queryset.order_by('-updated_at')


class TalentShowcaseDetailView(APIView):
    """
    Authenticated view of an individual candidate's profile, experiences, and education.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id_or_profile_id):
        try:
            val_uuid = uuid.UUID(str(user_id_or_profile_id))
            profile = get_object_or_404(
                ApplicantProfile.objects.select_related('user').prefetch_related('skills', 'experiences', 'educations'),
                Q(pk=val_uuid) | Q(user__id=val_uuid)
            )
        except ValueError:
            profile = get_object_or_404(
                ApplicantProfile.objects.select_related('user').prefetch_related('skills', 'experiences', 'educations'),
                user__username=user_id_or_profile_id
            )

        serializer = ApplicantProfileSerializer(profile)
        return Response({
            'success': True,
            'data': serializer.data
        })


class MarketplaceOverviewView(APIView):
    """
    High-level marketplace hub statistics, featured talents, and top hiring companies.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_talents = ApplicantProfile.objects.filter(user__is_active=True, is_open_to_work=True).count()
        total_companies = CompanyProfile.objects.filter(user__is_active=True).count()
        active_jobs = Job.objects.filter(status=Job.Status.PUBLISHED).count()

        featured_talents_qs = ApplicantProfile.objects.select_related('user').prefetch_related('skills', 'experiences').filter(
            user__is_active=True,
            is_open_to_work=True
        ).order_by('-updated_at')[:6]
        featured_talents = TalentMarketplaceListSerializer(featured_talents_qs, many=True).data

        featured_companies_qs = CompanyProfile.objects.select_related('industry', 'user').filter(
            user__is_active=True
        ).order_by('-updated_at')[:6]
        featured_companies = CompanyPublicShowcaseSerializer(featured_companies_qs, many=True).data

        # Top skills
        popular_skills_qs = Skill.objects.all()[:12]
        popular_skills = SkillSerializer(popular_skills_qs, many=True).data

        return Response({
            'success': True,
            'data': {
                'metrics': {
                    'total_talents': total_talents,
                    'total_companies': total_companies,
                    'active_jobs': active_jobs
                },
                'featured_talents': featured_talents,
                'featured_companies': featured_companies,
                'popular_skills': popular_skills
            }
        })
