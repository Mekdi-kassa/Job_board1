from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Reporter endpoints
    path('submit/', views.ReportSubmitView.as_view(), name='report-submit'),
    path('my-reports/', views.MyReportsListView.as_view(), name='my-reports-list'),
    path('my-reports/<uuid:pk>/', views.MyReportDetailView.as_view(), name='my-report-detail'),

    # Super Admin Moderation Console
    path('admin/all/', views.AdminReportListView.as_view(), name='admin-reports-list'),
    path('admin/<uuid:pk>/', views.AdminReportDetailView.as_view(), name='admin-report-detail'),
    path('admin/<uuid:pk>/resolve/', views.AdminReportResolveView.as_view(), name='admin-report-resolve'),
]
