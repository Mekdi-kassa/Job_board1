# user/tests.py
from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User
from .utils import generate_verification_token
import hashlib
import re


class UserRegistrationTestCase(APITestCase):
    """Tests for User Registration & Email Dispatch"""
    
    def setUp(self):
        self.register_url = reverse('user:register')
        self.applicant_data = {
            'email': 'applicant@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'applicant',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        self.company_data = {
            'email': 'company@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'role': 'company',
            'company_name': 'Acme Corp',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }

    def test_register_applicant_success_and_sends_verification_email(self):
        """User registers successfully, account is unverified/inactive, and verification email is sent"""
        response = self.client.post(self.register_url, self.applicant_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify user in database
        user = User.objects.get(email='applicant@example.com')
        self.assertFalse(user.is_verified, "User must NOT be verified immediately upon registration")
        self.assertFalse(user.is_active, "User must NOT be active before email verification")
        self.assertIsNotNone(user.email_verification_token, "Verification token hash must be stored")
        self.assertIsNotNone(user.email_verification_sent_at, "Sent timestamp must be recorded")
        self.assertEqual(user.role, User.Role.APPLICANT)
        
        # Verify email was dispatched
        self.assertEqual(len(mail.outbox), 1, "Verification email must be sent")
        email = mail.outbox[0]
        self.assertEqual(email.to, ['applicant@example.com'])
        self.assertIn("Verify Your Email", email.subject)
        self.assertIn("token=", email.body)
        self.assertIn(user.email, email.body)

    def test_register_company_success(self):
        """Company registration creates unverified company user and sends email"""
        response = self.client.post(self.register_url, self.company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='company@example.com')
        self.assertEqual(user.role, User.Role.COMPANY)
        self.assertFalse(user.is_verified)
        self.assertEqual(len(mail.outbox), 1)

    def test_register_fails_with_password_mismatch(self):
        """Registration fails when password and confirm_password differ"""
        data = self.applicant_data.copy()
        data['confirm_password'] = 'DifferentPassword123!'
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email=data['email']).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_register_fails_with_duplicate_email(self):
        """Registration fails when email already exists"""
        self.client.post(self.register_url, self.applicant_data, format='json')
        mail.outbox.clear()
        
        # Second registration attempt with identical email
        response = self.client.post(self.register_url, self.applicant_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_register_fails_with_invalid_role(self):
        """Registration fails when role is invalid"""
        data = self.applicant_data.copy()
        data['role'] = 'invalid_role'
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailVerificationTestCase(APITestCase):
    """Tests for Email Verification Logic & Token Validation"""

    def setUp(self):
        self.verify_url = reverse('user:verify-email')
        self.register_url = reverse('user:register')
        
        # Register a test user
        self.user_data = {
            'email': 'verifytest@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'applicant',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        self.client.post(self.register_url, self.user_data, format='json')
        self.user = User.objects.get(email='verifytest@example.com')
        
        # Extract raw token sent in email
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        token_match = re.search(r'token=([A-Za-z0-9_-]+)', email_body)
        self.assertIsNotNone(token_match, "Token should be present in email body")
        self.raw_token = token_match.group(1)

    def test_verify_email_success_via_post(self):
        """Valid token verification via POST activates and verifies the user"""
        payload = {
            'email': self.user.email,
            'token': self.raw_token
        }
        response = self.client.post(self.verify_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Reload user from DB
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified, "User must be marked verified")
        self.assertTrue(self.user.is_active, "User must be marked active")
        self.assertIsNotNone(self.user.email_verified_at)
        self.assertIsNone(self.user.email_verification_token, "Token should be cleared after verification")

    def test_verify_email_success_via_get(self):
        """Valid token verification via GET query params (clicking email link directly)"""
        response = self.client.get(f"{self.verify_url}?token={self.raw_token}&email={self.user.email}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.user.is_active)

    def test_verify_email_fails_with_wrong_token(self):
        """Verification fails when an incorrect token is provided"""
        payload = {
            'email': self.user.email,
            'token': 'completely_wrong_token_12345'
        }
        response = self.client.post(self.verify_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertFalse(self.user.is_active)

    def test_verify_email_fails_with_expired_token(self):
        """Verification fails when token has expired (> 7 days)"""
        # Backdate the verification timestamp by 8 days
        self.user.email_verification_sent_at = timezone.now() - timedelta(days=8)
        self.user.save()
        
        payload = {
            'email': self.user.email,
            'token': self.raw_token
        }
        response = self.client.post(self.verify_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data['message'].lower())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)

    def test_verify_email_fails_for_already_verified_user(self):
        """Verification fails if user is already verified"""
        # First verification
        self.client.post(self.verify_url, {'email': self.user.email, 'token': self.raw_token}, format='json')
        
        # Second verification attempt
        response = self.client.post(self.verify_url, {'email': self.user.email, 'token': self.raw_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_fails_for_nonexistent_email(self):
        """Verification fails for an email not in the database"""
        response = self.client.post(self.verify_url, {'email': 'ghost@example.com', 'token': self.raw_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResendVerificationTestCase(APITestCase):
    """Tests for Resending Verification Emails"""

    def setUp(self):
        self.resend_url = reverse('user:resend-verification')
        self.register_url = reverse('user:register')
        
        self.user_data = {
            'email': 'resendtest@example.com',
            'first_name': 'Resend',
            'last_name': 'Test',
            'role': 'applicant',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        self.client.post(self.register_url, self.user_data, format='json')
        self.user = User.objects.get(email='resendtest@example.com')
        mail.outbox.clear()

    def test_resend_verification_success(self):
        """Unverified user can request a fresh verification link"""
        old_token = self.user.email_verification_token
        
        response = self.client.post(self.resend_url, {'email': self.user.email}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(mail.outbox), 1)
        
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email_verification_token, old_token, "A new token must be generated")

    def test_resend_verification_fails_if_already_verified(self):
        """Resend request fails if the user is already verified"""
        self.user.is_verified = True
        self.user.is_active = True
        self.user.save()
        
        response = self.client.post(self.resend_url, {'email': self.user.email}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)


class AuthenticationAndLoginTestCase(APITestCase):
    """Tests for Authentication: Login Blocked Before Verification, Allowed After"""

    def setUp(self):
        self.register_url = reverse('user:register')
        self.login_url = reverse('user:login')
        self.verify_url = reverse('user:verify-email')
        self.profile_url = reverse('user:profile')
        self.refresh_url = reverse('user:refresh')
        self.logout_url = reverse('user:logout')
        
        self.password = 'SecurePassword123!'
        self.user_data = {
            'email': 'logintest@example.com',
            'first_name': 'Login',
            'last_name': 'Tester',
            'role': 'applicant',
            'password': self.password,
            'confirm_password': self.password
        }
        
        # Register user
        self.client.post(self.register_url, self.user_data, format='json')
        self.user = User.objects.get(email='logintest@example.com')
        
        # Extract verification token
        email_body = mail.outbox[0].body
        token_match = re.search(r'token=([A-Za-z0-9_-]+)', email_body)
        self.raw_token = token_match.group(1)

    def test_login_blocked_before_email_verification(self):
        """User cannot login before verifying email"""
        login_payload = {
            'email': self.user.email,
            'password': self.password
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success', False))
        # Ensure error message mentions email verification
        error_msg = str(response.data.get('errors', {}))
        self.assertIn("verify your email", error_msg.lower())

    def test_full_auth_flow_register_then_verify_then_login_success(self):
        """Full end-to-end authentication flow: Register -> Blocked -> Verify -> Login Success"""
        login_payload = {
            'email': self.user.email,
            'password': self.password
        }
        
        # Step 1: Login attempt before verification fails
        step1_res = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(step1_res.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Verify email using received token
        verify_payload = {
            'email': self.user.email,
            'token': self.raw_token
        }
        step2_res = self.client.post(self.verify_url, verify_payload, format='json')
        self.assertEqual(step2_res.status_code, status.HTTP_200_OK)
        
        # Step 3: Login attempt after verification succeeds
        step3_res = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(step3_res.status_code, status.HTTP_200_OK)
        self.assertTrue(step3_res.data['success'])
        self.assertIn('access', step3_res.data['data'])
        self.assertIn('refresh', step3_res.data['data'])
        self.assertEqual(step3_res.data['data']['user']['email'], self.user.email)
        
        # Step 4: Access protected profile using JWT token
        access_token = step3_res.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        profile_res = self.client.get(self.profile_url)
        self.assertEqual(profile_res.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_res.data['data']['email'], self.user.email)

    def test_login_fails_with_incorrect_password(self):
        """Verified user entering wrong password is rejected"""
        # Verify the user first
        self.client.post(self.verify_url, {'email': self.user.email, 'token': self.raw_token}, format='json')
        
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'WrongPassword123!'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_fails_for_suspended_user(self):
        """Suspended user is blocked from logging in"""
        # Verify user
        self.client.post(self.verify_url, {'email': self.user.email, 'token': self.raw_token}, format='json')
        
        # Suspend user
        self.user.refresh_from_db()
        self.user.is_suspended = True
        self.user.save()
        
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': self.password
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("suspended", str(response.data).lower())

    def test_token_refresh_and_logout(self):
        """Test token refresh and logout blacklist flow"""
        # Verify and login
        self.client.post(self.verify_url, {'email': self.user.email, 'token': self.raw_token}, format='json')
        login_res = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': self.password
        }, format='json')
        
        refresh_token = login_res.data['data']['refresh']
        access_token = login_res.data['data']['access']
        
        # Test token refresh (rotates refresh token and returns new one)
        refresh_res = self.client.post(self.refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_res.data['data'])
        self.assertIn('refresh', refresh_res.data['data'])
        new_refresh_token = refresh_res.data['data']['refresh']
        new_access_token = refresh_res.data['data']['access']
        
        # Original token was blacklisted on rotation
        old_token_res = self.client.post(self.refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(old_token_res.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test logout with active rotated refresh token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        logout_res = self.client.post(self.logout_url, {'refresh': new_refresh_token}, format='json')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)
        
        # Trying to refresh with logged-out token must fail
        self.client.credentials()  # Clear auth header
        second_refresh_res = self.client.post(self.refresh_url, {'refresh': new_refresh_token}, format='json')
        self.assertEqual(second_refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)
