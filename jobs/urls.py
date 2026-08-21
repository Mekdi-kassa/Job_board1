from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Public Job Browsing & Discovery
    path('', views.JobPublicListView.as_view(), name='public-job-list'),
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('featured/', views.FeaturedJobsListView.as_view(), name='featured-jobs'),
    
    # Company Job Management (Must be before <str:slug_or_id> wildcard)
    path('create/', views.CompanyJobCreateView.as_view(), name='company-job-create'),
    path('my-jobs/', views.CompanyMyJobsListView.as_view(), name='company-my-jobs'),
    path('my-jobs/<uuid:pk>/', views.CompanyJobDetailManageView.as_view(), name='company-job-detail'),
    path('my-jobs/<uuid:pk>/toggle-status/', views.CompanyJobToggleStatusView.as_view(), name='company-job-toggle-status'),

    # Admin Management
    path('admin/all/', views.AdminJobListView.as_view(), name='admin-all-jobs'),
    path('admin/<uuid:pk>/feature/', views.AdminJobToggleFeatureView.as_view(), name='admin-job-toggle-feature'),
    path('admin/categories/', views.AdminCategoryManageView.as_view(), name='admin-category-create'),
    path('admin/categories/<uuid:pk>/', views.AdminCategoryManageView.as_view(), name='admin-category-update'),

    # Public Job Detail (Wildcard lookup by slug or UUID)
    path('<str:slug_or_id>/', views.JobPublicDetailView.as_view(), name='public-job-detail'),
]
