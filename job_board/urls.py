# job_board/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # User app (all user-related endpoints)
    path('api/', include('user.urls')),  # This includes all user URLs
    
    # Jobs app (all job postings, categories, search, company job management)
    path('api/jobs/', include('jobs.urls')),
    
    # Applications app (job applications, applicant tracking, company candidate review pipeline)
    path('api/applications/', include('applications.urls')),
    
    # Profiles app (company branding showcase, applicant resumes, skills, experience, education)
    path('api/profiles/', include('profiles.urls')),
    
    # Search & Discovery engine (unified search, autocomplete suggestions, facets, trending)
    path('api/search/', include('search.urls')),
    
    # Dashboards & Analytics (Company hiring pipeline, applicant tracker, admin platform analytics)
    path('api/dashboard/', include('dashboard.urls')),
    
    # In-App Notifications & Email Alerts
    path('api/notifications/', include('notifications.urls')),
    
    # Reports & Super Admin Moderation Console
    path('api/reports/', include('reports.urls')),
]

from django.views.static import serve
from django.urls import re_path

# Serve media files in all environments (fallback when external S3/Cloudinary not configured)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]