# user/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from . import views

app_name = 'user'

urlpatterns = [
    # ============================================================
    # AUTHENTICATION ENDPOINTS (Public)
    # ============================================================
    
    # Register a new user
    # POST /api/auth/register/
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    
    # Login user and get JWT tokens
    # POST /api/auth/login/
    path('auth/login/', views.LoginView.as_view(), name='login'),
    
    # Refresh JWT access token
    # POST /api/auth/refresh/
    path('auth/refresh/', views.RefreshTokenView.as_view(), name='refresh'),
    
    # Verify JWT token is valid
    # POST /api/auth/verify/
    path('auth/verify/', TokenVerifyView.as_view(), name='verify'),
    
    # Logout user (blacklist refresh token)
    # POST /api/auth/logout/
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # ============================================================
    # EMAIL VERIFICATION ENDPOINTS (Public)
    # ============================================================
    
    # Verify email with token
    # POST /api/auth/verify-email/
    path('auth/verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    
    # Resend verification email
    # POST /api/auth/resend-verification/
    path('auth/resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    
    # ============================================================
    # PROFILE ENDPOINTS (Authenticated Users)
    # ============================================================
    
    # Get or update current user's profile
    # GET /api/profile/ - Get profile
    # PATCH /api/profile/ - Update profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # ============================================================
    # SUPER ADMIN ENDPOINTS (Super Admin Only)
    # ============================================================
    
    # List all users with optional filters
    # GET /api/admin/users/ - List all users
    # GET /api/admin/users/?role=company - Filter by role
    # GET /api/admin/users/?role=applicant - Filter by role
    # GET /api/admin/users/?is_active=true - Filter by status
    path('admin/users/', views.AllUsersView.as_view(), name='admin-users'),
    
    # Get, update, or delete a specific user
    # GET /api/admin/users/<uuid>/ - Get user details
    # PATCH /api/admin/users/<uuid>/ - Update user
    # DELETE /api/admin/users/<uuid>/ - Delete user
    path('admin/users/<uuid:user_id>/', views.UserDetailView.as_view(), name='admin-user-detail'),
    
    # Suspend or activate a user
    # POST /api/admin/users/<uuid>/suspend/
    # Body: {"action": "suspend"} or {"action": "activate"}
    path('admin/users/<uuid:user_id>/suspend/', views.SuspendUserView.as_view(), name='admin-suspend-user'),
]