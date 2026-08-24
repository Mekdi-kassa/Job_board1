from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # Company Profile Endpoints
    path('company/me/', views.CompanyMyProfileView.as_view(), name='company-my-profile'),
    path('company/me/logo/', views.CompanyLogoUploadView.as_view(), name='company-logo-upload'),
    path('companies/', views.CompanyPublicListView.as_view(), name='company-public-list'),
    path('companies/<str:slug_or_id>/', views.CompanyPublicShowcaseDetailView.as_view(), name='company-public-detail'),

    # Applicant Profile Endpoints
    path('applicant/me/', views.ApplicantMyProfileView.as_view(), name='applicant-my-profile'),
    path('applicant/me/avatar/', views.ApplicantAvatarUploadView.as_view(), name='applicant-avatar-upload'),
    path('applicant/me/resume/', views.ApplicantResumeUploadView.as_view(), name='applicant-resume-upload'),
    path('applicant/me/experience/', views.ApplicantWorkExperienceListCreateView.as_view(), name='applicant-experience-list-create'),
    path('applicant/me/experience/<uuid:pk>/', views.ApplicantWorkExperienceDetailView.as_view(), name='applicant-experience-detail'),
    path('applicant/me/education/', views.ApplicantEducationListCreateView.as_view(), name='applicant-education-list-create'),
    path('applicant/me/education/<uuid:pk>/', views.ApplicantEducationDetailView.as_view(), name='applicant-education-detail'),

    # Skills Endpoints
    path('skills/', views.SkillListCreateView.as_view(), name='skills-list-create'),

    # Talent & Community Marketplace Endpoints
    path('marketplace/overview/', views.MarketplaceOverviewView.as_view(), name='marketplace-overview'),
    path('talent/', views.TalentMarketplaceListView.as_view(), name='talent-list'),
    path('talent/<str:user_id_or_profile_id>/', views.TalentShowcaseDetailView.as_view(), name='talent-detail'),
]
