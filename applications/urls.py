from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    # Applicant Endpoints
    path('apply/<uuid:job_id>/', views.JobApplyView.as_view(), name='apply-job'),
    path('my-applications/', views.ApplicantMyApplicationsListView.as_view(), name='my-applications-list'),
    path('my-applications/<uuid:pk>/', views.ApplicantApplicationDetailView.as_view(), name='my-application-detail'),
    path('my-applications/<uuid:pk>/withdraw/', views.ApplicantApplicationWithdrawView.as_view(), name='my-application-withdraw'),

    # Company Candidate Pipeline Endpoints
    path('job/<uuid:job_id>/', views.CompanyJobApplicationsListView.as_view(), name='company-job-candidates'),
    path('company/all/', views.CompanyAllApplicationsListView.as_view(), name='company-all-candidates'),
    path('company/<uuid:pk>/', views.CompanyApplicationDetailReviewView.as_view(), name='company-candidate-detail'),
    path('company/<uuid:pk>/status/', views.CompanyApplicationDetailReviewView.as_view(), name='company-candidate-status-update'),

    # Super Admin Endpoint
    path('admin/all/', views.AdminApplicationListView.as_view(), name='admin-all-applications'),
]
