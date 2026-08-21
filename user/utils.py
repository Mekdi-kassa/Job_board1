# user/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import secrets
import hashlib


def generate_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)


def send_verification_email(user):
    """
    Send email verification link to user
    Returns: (success: bool, message: str)
    """
    try:
        # Generate token
        token = generate_verification_token()
        
        # Hash the token for storage (security)
        hashed_token = hashlib.sha256(token.encode()).hexdigest()
        
        # Save hashed token to user
        user.email_verification_token = hashed_token
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        
        # Build verification links
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        verification_link = f"{frontend_url}/verify-email?token={token}&email={user.email}"
        direct_api_link = f"http://localhost:8000/api/auth/verify-email/?token={token}&email={user.email}"
        
        # Email subject
        subject = "🎯 Verify Your Email - Job Board"
        
        # HTML Email with 100% inline CSS (compatible with Gmail, Outlook, Apple Mail)
        html_message = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f6f8; padding: 40px 10px;">
        <tr>
            <td align="center">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #2563eb; padding: 32px 24px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">🎯 Job Board</h1>
                            <p style="color: #bfdbfe; margin: 8px 0 0 0; font-size: 15px;">Account Email Verification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 36px 32px;">
                            <h2 style="color: #1e293b; margin: 0 0 16px 0; font-size: 20px; font-weight: 600;">Hello, {user.get_full_name()}!</h2>
                            <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
                                Thank you for creating an account with Job Board. To complete your registration and activate your login, please verify your email address.
                            </p>
                            
                            <!-- Primary Button -->
                            <div style="text-align: center; margin: 32px 0;">
                                <a href="{direct_api_link}" style="background-color: #2563eb; color: #ffffff !important; display: inline-block; padding: 16px 36px; font-size: 16px; font-weight: 700; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 8px rgba(37,99,235,0.25);">
                                    ✅ Verify Email Address
                                </a>
                            </div>
                            
                            <!-- Fallback Link -->
                            <div style="margin: 28px 0; padding: 16px; background-color: #f8fafc; border-left: 4px solid #2563eb; border-radius: 4px;">
                                <p style="margin: 0 0 8px 0; color: #334155; font-size: 13px; font-weight: 600;">Or copy and paste this link in your browser:</p>
                                <a href="{direct_api_link}" style="color: #2563eb; font-size: 13px; word-break: break-all; text-decoration: underline;">
                                    {direct_api_link}
                                </a>
                            </div>
                            
                            <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 24px 0 0 0;">
                                ⚠️ <strong>Note:</strong> This verification link will expire in 7 days.<br>
                                If you did not register for this account, please disregard this email.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="color: #94a3b8; font-size: 12px; margin: 0;">&copy; 2026 Job Board Platform. All rights reserved.</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
        
        # Plain text version
        plain_message = f"""Hello {user.get_full_name()}!

Thank you for registering with Job Board.

Please verify your email address by clicking the link below:
{direct_api_link}

This verification link will expire in 7 days.

If you did not create an account, please ignore this email.

---
Job Board Team"""
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True, "Verification email sent successfully"
        
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False, f"Failed to send email: {str(e)}"


def verify_email_token(user, token):
    """
    Verify the email verification token
    Returns: (success: bool, message: str)
    """
    if not user or not user.email_verification_token:
        return False, "No verification token found"
    
    # Hash the provided token
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    
    # Check if token matches
    if user.email_verification_token != hashed_token:
        return False, "Invalid verification token"
    
    # Check if token expired
    if user.is_email_verification_expired():
        return False, "Verification token has expired. Please request a new one."
    
    # Mark user as verified
    user.is_verified = True
    user.is_active = True
    user.email_verified_at = timezone.now()
    user.email_verification_token = None
    user.save(update_fields=['is_verified', 'is_active', 'email_verified_at', 'email_verification_token'])
    
    return True, "Email verified successfully!"


def resend_verification_email(user):
    """
    Resend verification email to user
    Returns: (success: bool, message: str)
    """
    if user.is_verified:
        return False, "Email already verified"
    
    return send_verification_email(user)


def custom_exception_handler(exc, context):
    """Custom DRF exception handler providing consistent response structure"""
    from rest_framework.views import exception_handler
    
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data = {
            'success': False,
            'errors': response.data
        }
        
    return response