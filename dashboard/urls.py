from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Company Hiring Dashboard
    path('company/', views.CompanyDashboardView.as_view(), name='company-dashboard'),

    # Applicant Tracking & Recommendations Dashboard
    path('applicant/', views.ApplicantDashboardView.as_view(), name='applicant-dashboard'),

    # Super Admin Platform Analytics
    path('admin/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
]
