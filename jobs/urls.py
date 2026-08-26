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

    # Company alias routes for API client compatibility
    path('company/create/', views.CompanyJobCreateView.as_view(), name='company-job-create-alt'),
    path('company/my-jobs/', views.CompanyMyJobsListView.as_view(), name='company-my-jobs-alt'),
    path('company/<uuid:pk>/', views.CompanyJobDetailManageView.as_view(), name='company-job-detail-alt'),
    path('company/<uuid:pk>/update/', views.CompanyJobDetailManageView.as_view(), name='company-job-update'),
    path('company/<uuid:pk>/toggle-status/', views.CompanyJobToggleStatusView.as_view(), name='company-job-toggle-status-alt'),
    path('company/<uuid:pk>/delete/', views.CompanyJobDetailManageView.as_view(), name='company-job-delete'),

    # Admin Management
    path('admin/all/', views.AdminJobListView.as_view(), name='admin-all-jobs'),
    path('admin/<uuid:pk>/', views.AdminJobDetailManageView.as_view(), name='admin-job-manage'),
    path('admin/<uuid:pk>/feature/', views.AdminJobToggleFeatureView.as_view(), name='admin-job-toggle-feature'),
    path('admin/categories/', views.AdminCategoryManageView.as_view(), name='admin-category-create'),
    path('admin/categories/<uuid:pk>/', views.AdminCategoryManageView.as_view(), name='admin-category-update'),

    # Ecommerce Product Marketplace
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/my-products/', views.MyProductsListView.as_view(), name='my-products-list'),
    path('products/<str:slug_or_id>/', views.ProductDetailManageView.as_view(), name='product-detail-manage'),
    path('products/<str:slug_or_id>/inquire/', views.ProductInquiryCreateView.as_view(), name='product-inquiry-create'),

    # Public Job Detail (Wildcard lookup by slug or UUID)
    path('<str:slug_or_id>/', views.JobPublicDetailView.as_view(), name='public-job-detail'),
]
