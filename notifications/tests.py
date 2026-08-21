from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from applications.models import Application
from notifications.models import Notification
from notifications.services import (
    create_and_send_notification,
    notify_application_status_update,
    notify_new_candidate
)


class NotificationAPITests(APITestCase):
    """Automated tests for In-App Notifications and Alerts"""

    def setUp(self):
        # Create Category
        self.category = Category.objects.create(
            name="Technology & IT",
            description="Tech jobs"
        )

        # Create Company User
        self.company_user = User.objects.create_user(
            email="company@example.com",
            password="SecurePassword123!",
            first_name="TechCorp",
            last_name="Inc",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )

        # Create Applicant 1
        self.applicant_1 = User.objects.create_user(
            email="alice@example.com",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="Smith",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Create Applicant 2
        self.applicant_2 = User.objects.create_user(
            email="bob@example.com",
            password="SecurePassword123!",
            first_name="Bob",
            last_name="Jones",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Create Published Job
        self.job = Job.objects.create(
            company=self.company_user,
            category=self.category,
            title="Senior Python Backend Developer",
            description="Django backend role.",
            requirements="Python & Django.",
            status=Job.Status.PUBLISHED
        )

        # Create Sample Notifications for Applicant 1
        self.notif_1 = Notification.objects.create(
            recipient=self.applicant_1,
            sender=self.company_user,
            notification_type=Notification.NotificationType.APPLICATION_STATUS_UPDATE,
            title="Application Shortlisted",
            message="Your application has been moved to Shortlisted.",
            action_url="/api/applications/my-applications/123/",
            is_read=False
        )

        self.notif_2 = Notification.objects.create(
            recipient=self.applicant_1,
            sender=None,
            notification_type=Notification.NotificationType.SYSTEM_ANNOUNCEMENT,
            title="Welcome to Job Board",
            message="Explore newly posted tech jobs today!",
            is_read=True
        )

    def test_list_notifications_authenticated(self):
        """Applicant lists all their in-app notifications"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_filter_unread_notifications(self):
        """Filter only unread notifications (?is_read=false)"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:notification-list') + "?is_read=false"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.notif_1.id))

    def test_unread_count_badge_endpoint(self):
        """Unread count endpoint returns accurate count"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:unread-count')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['unread_count'], 1)

    def test_mark_single_notification_as_read(self):
        """Mark single notification as read"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:mark-read', kwargs={'pk': self.notif_1.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['is_read'])
        
        self.notif_1.refresh_from_db()
        self.assertTrue(self.notif_1.is_read)

    def test_mark_all_notifications_as_read(self):
        """Mark all unread notifications as read"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:mark-all-read')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 1)
        
        # Verify unread count is now 0
        unread_count = Notification.objects.filter(recipient=self.applicant_1, is_read=False).count()
        self.assertEqual(unread_count, 0)

    def test_delete_notification(self):
        """Applicant deletes notification"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('notifications:delete-notification', kwargs={'pk': self.notif_2.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Notification.objects.filter(id=self.notif_2.id).exists())

    def test_user_cannot_access_other_user_notification(self):
        """Applicant 2 cannot mark read or delete Applicant 1's notification"""
        self.client.force_authenticate(user=self.applicant_2)
        url = reverse('notifications:mark-read', kwargs={'pk': self.notif_1.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_notifications(self):
        """Unauthenticated guest receives 401 Unauthorized"""
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_notification_service_integration_on_status_change(self):
        """Application status change triggers in-app notification for applicant"""
        app = Application.objects.create(
            job=self.job,
            applicant=self.applicant_1,
            resume_url="https://example.com/resume.pdf",
            status=Application.Status.PENDING
        )

        app.status = Application.Status.INTERVIEWED
        app.save()

        notif = notify_application_status_update(app)
        self.assertEqual(notif.recipient, self.applicant_1)
        self.assertEqual(notif.notification_type, Notification.NotificationType.APPLICATION_STATUS_UPDATE)
        self.assertIn("Interview Scheduled", notif.message)
