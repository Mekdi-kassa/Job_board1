# user/views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, 
    RefreshTokenSerializer, LogoutSerializer, VerifyEmailSerializer,
    ResendVerificationSerializer, RequestPasswordResetSerializer,
    ResetPasswordConfirmSerializer
)
from .permissions import IsSuperAdmin, IsCompany, IsApplicant
from .utils import (
    send_verification_email, verify_email_token,
    send_password_reset_email, reset_password_with_token
)
from .models import User
from django.http import HttpResponse
import os
import logging
import traceback

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """User Registration with Email Verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            print("📝 Registration attempt for:", request.data.get('email'))
            
            serializer = RegisterSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    # Save user (this will also send email)
                    user = serializer.save()
                    print(f"✅ User created: {user.email}, ID: {user.id}")
                    
                    return Response({
                        'success': True,
                        'message': 'Registration successful. We have sent a verification link to your email. Please verify to login.',
                        'data': UserSerializer(user).data
                    }, status=status.HTTP_201_CREATED)
                    
                except Exception as e:
                    print(f"❌ User creation failed: {str(e)}")
                    print(traceback.format_exc())
                    return Response({
                        'success': False,
                        'message': f'User creation failed: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            print(f"❌ Validation failed: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"❌ Registration error: {str(e)}")
            print(traceback.format_exc())
            return Response({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyEmailView(APIView):
    """Verify User Email (supports POST body or GET query params)"""
    permission_classes = [permissions.AllowAny]
    
    def _verify(self, data):
        serializer = VerifyEmailSerializer(data=data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = serializer.validated_data['token']
            
            success, message = verify_email_token(user, token)
            
            if success:
                return Response({
                    'success': True,
                    'message': message,
                    'data': {
                        'email': user.email,
                        'verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        try:
            accept_header = request.headers.get('Accept', '')
            wants_html = 'text/html' in accept_header and 'application/json' not in accept_header

            serializer = VerifyEmailSerializer(data=request.query_params)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                token = serializer.validated_data['token']
                success, message = verify_email_token(user, token)

                if wants_html:
                    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
                    if success:
                        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3;url={frontend_url}/login">
    <title>Email Verified - Job Board</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh;">
    <div style="max-width: 480px; width: 90%; background: #ffffff; border-radius: 20px; padding: 40px 32px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <div style="width: 64px; height: 64px; background-color: #d1fae5; color: #059669; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 32px;">
            ✓
        </div>
        <h1 style="color: #0f172a; font-size: 24px; font-weight: 700; margin: 20px 0 8px 0;">Email Verified!</h1>
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;">
            Your account (<strong>{user.email}</strong>) is now verified and active.<br>
            Redirecting you to sign in...
        </p>
        <a href="{frontend_url}/login" style="display: block; width: 100%; box-sizing: border-box; background-color: #2563eb; color: #ffffff !important; padding: 14px 24px; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 12px rgba(37,99,235,0.25);">
            Proceed to Sign In →
        </a>
    </div>
</body>
</html>"""
                        return HttpResponse(html_content, content_type="text/html")
                    else:
                        html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Verification Failed</title></head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh;">
    <div style="max-width: 480px; width: 90%; background: #ffffff; border-radius: 20px; padding: 40px 32px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <div style="width: 64px; height: 64px; background-color: #fee2e2; color: #dc2626; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 32px;">
            ✕
        </div>
        <h1 style="color: #0f172a; font-size: 24px; font-weight: 700; margin: 20px 0 8px 0;">Verification Failed</h1>
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 28px 0;">{message}</p>
        <a href="{frontend_url}/login" style="display: block; width: 100%; box-sizing: border-box; background-color: #2563eb; color: #ffffff !important; padding: 14px 24px; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 16px;">
            Go to Sign In
        </a>
    </div>
</body>
</html>"""
                        return HttpResponse(html_content, content_type="text/html", status=400)

                if success:
                    return Response({
                        'success': True,
                        'message': message,
                        'data': {
                            'email': user.email,
                            'verified_at': user.email_verified_at.isoformat() if user.email_verified_at else None
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'success': False, 'message': message}, status=status.HTTP_400_BAD_REQUEST)

            if wants_html:
                return HttpResponse("<h3>Invalid verification link</h3>", content_type="text/html", status=400)

            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Email verification error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Verification failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        try:
            return self._verify(request.data)
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Verification failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResendVerificationView(APIView):
    """Resend Email Verification"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            serializer = ResendVerificationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                
                if user.is_verified:
                    return Response({
                        'success': False,
                        'message': 'Email already verified.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                success, message = send_verification_email(user)
                
                if success:
                    return Response({
                        'success': True,
                        'message': 'A new verification link has been sent to your email.'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': message
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Resend verification error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to resend verification email.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """User Login"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if serializer.is_valid():
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'data': serializer.validated_data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Login failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RefreshTokenView(TokenRefreshView):
    """Refresh JWT Token"""
    serializer_class = RefreshTokenSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({
            'success': True,
            'message': 'Token refreshed successfully',
            'data': response.data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """User Logout"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = LogoutSerializer(data=request.data)
            if serializer.is_valid():
                refresh_token = serializer.validated_data['refresh']
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                return Response({
                    'success': True,
                    'message': 'Logout successful'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """Get/Update User Profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def patch(self, request):
        try:
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'data': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to update profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AllUsersView(APIView):
    """Get all users (Super Admin only)"""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        users = User.objects.all().order_by('-created_at')
        role = request.query_params.get('role')
        if role:
            users = users.filter(role=role)
        
        serializer = UserSerializer(users, many=True)
        return Response({
            'success': True,
            'count': users.count(),
            'data': serializer.data
        })


class UserDetailView(APIView):
    """Get/Update/Delete specific user (Super Admin only)"""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user.id == request.user.id:
                return Response({
                    'success': False,
                    'message': 'Cannot modify your own account through this endpoint.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'User updated successfully',
                    'data': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user.id == request.user.id:
                return Response({
                    'success': False,
                    'message': 'Cannot delete your own account.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            user.delete()
            return Response({
                'success': True,
                'message': 'User deleted successfully'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SuspendUserView(APIView):
    """Suspend or Activate user (Super Admin only)"""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            if user.id == request.user.id:
                return Response({
                    'success': False,
                    'message': 'Cannot suspend your own account.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            action = request.data.get('action')
            if action not in ['suspend', 'activate']:
                return Response({
                    'success': False,
                    'message': 'Action must be "suspend" or "activate"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if action == 'suspend':
                user.is_suspended = True
                user.is_active = False
                message = 'User suspended successfully'
            else:
                user.is_suspended = False
                user.is_active = True
                message = 'User activated successfully'
            
            user.save()
            
            return Response({
                'success': True,
                'message': message
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class RequestPasswordResetView(APIView):
    """Request Password Reset Link via Email"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email__iexact=email).first()
            if user:
                success, message = send_password_reset_email(user)
                if success:
                    return Response({
                        'success': True,
                        'message': 'Password reset link sent to your email.'
                    }, status=status.HTTP_200_OK)
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordConfirmView(APIView):
    """Confirm Password Reset with Token"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            success, message = reset_password_with_token(user, token, new_password)
            if success:
                return Response({
                    'success': True,
                    'message': message
                }, status=status.HTTP_200_OK)
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)