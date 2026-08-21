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
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)