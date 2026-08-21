from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from reports.models import Report


class ReportsAPITestsBase(APITestCase):
    """Base setup for Reports & Admin Moderation tests"""
    def setUp(self):
        # Create Category
        self.category = Category.objects.create(
            name="Technology & IT",
            description="Tech jobs"
        )

        # Create Offending Company User
        self.offending_company = User.objects.create_user(
            email="scammer@example.com",
            password="SecurePassword123!",
            first_name="FakeCorp",
            last_name="Scam",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )

        # Create Offending Job
        self.offending_job = Job.objects.create(
            company=self.offending_company,
            category=self.category,
            title="Suspicious High Paying Work From Home",
            description="Send money upfront for equipment.",
            requirements="None.",
            status=Job.Status.PUBLISHED,
            is_featured=True
        )

        # Create Legitimate Applicant Reporter
        self.reporter_user = User.objects.create_user(
            email="honest_applicant@example.com",
            password="SecurePassword123!",
            first_name="Honest",
            last_name="User",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Create Another User
        self.other_user = User.objects.create_user(
            email="other_user@example.com",
            password="SecurePassword123!",
            first_name="Other",
            last_name="Person",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Create Super Admin
        self.admin_user = User.objects.create_superuser(
            email="moderator_admin@example.com",
            password="SecurePassword123!",
            first_name="Admin",
            last_name="Moderator"
        )


class ReportSubmissionTests(ReportsAPITestsBase):
    """Tests for submitting reports against jobs and users"""

    def test_submit_report_against_job(self):
        """User successfully submits report against a suspicious job"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:report-submit')
        data = {
            'target_type': Report.TargetType.JOB,
            'job_id': str(self.offending_job.id),
            'reason': Report.Reason.SPAM_OR_SCAM,
            'description': 'This job is asking for wire transfer before sending contract.',
            'evidence_url': 'https://example.com/screenshot.png'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(Report.objects.count(), 1)

        report = Report.objects.first()
        self.assertEqual(report.reported_job, self.offending_job)
        self.assertEqual(report.reporter, self.reporter_user)
        self.assertEqual(report.status, Report.Status.PENDING)

    def test_submit_report_against_user(self):
        """User submits report against a fraudulent company account"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:report-submit')
        data = {
            'target_type': Report.TargetType.USER,
            'user_id': str(self.offending_company.id),
            'reason': Report.Reason.IMPERSONATION,
            'description': 'This user is impersonating a well-known tech firm.'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.filter(reported_user=self.offending_company).count(), 1)

    def test_cannot_report_self(self):
        """User is prevented from reporting their own account"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:report-submit')
        data = {
            'target_type': Report.TargetType.USER,
            'user_id': str(self.reporter_user.id),
            'reason': Report.Reason.OTHER,
            'description': 'Reporting myself for no reason.'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_short_description_fails(self):
        """Description under 10 chars fails validation"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:report-submit')
        data = {
            'target_type': Report.TargetType.JOB,
            'job_id': str(self.offending_job.id),
            'reason': Report.Reason.SPAM_OR_SCAM,
            'description': 'Scam!'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_cannot_submit_report(self):
        """Guest cannot submit report"""
        url = reverse('reports:report-submit')
        response = self.client.post(url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReporterTrackingTests(ReportsAPITestsBase):
    """Tests for reporters tracking their own reports"""

    def setUp(self):
        super().setUp()
        self.report = Report.objects.create(
            reporter=self.reporter_user,
            target_type=Report.TargetType.JOB,
            reported_job=self.offending_job,
            reason=Report.Reason.SPAM_OR_SCAM,
            description='This job posting is clearly fraudulent.'
        )

    def test_list_my_reports(self):
        """Reporter lists their submitted reports"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:my-reports-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.report.id))

    def test_other_user_cannot_view_my_report(self):
        """Other user cannot access someone else's submitted report"""
        self.client.force_authenticate(user=self.other_user)
        url = reverse('reports:my-report-detail', kwargs={'pk': self.report.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminModerationConsoleTests(ReportsAPITestsBase):
    """Tests for Super Admin moderation console and automated actions"""

    def setUp(self):
        super().setUp()
        self.report_job = Report.objects.create(
            reporter=self.reporter_user,
            target_type=Report.TargetType.JOB,
            reported_job=self.offending_job,
            reason=Report.Reason.SPAM_OR_SCAM,
            description='Scam job demanding fees.'
        )
        self.report_user = Report.objects.create(
            reporter=self.reporter_user,
            target_type=Report.TargetType.USER,
            reported_user=self.offending_company,
            reason=Report.Reason.IMPERSONATION,
            description='Scam company profile.'
        )

    def test_admin_list_all_reports(self):
        """Super Admin lists all platform reports"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('reports:admin-reports-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_admin_resolve_job_removed(self):
        """Super Admin resolves report with JOB_REMOVED action closing the offending job"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('reports:admin-report-resolve', kwargs={'pk': self.report_job.id})
        data = {
            'status': Report.Status.ACTION_TAKEN,
            'action_taken': Report.ActionTaken.JOB_REMOVED,
            'admin_notes': 'Confirmed scam posting. Removed job listing.'
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify job was closed
        self.offending_job.refresh_from_db()
        self.assertEqual(self.offending_job.status, Job.Status.CLOSED)
        self.assertFalse(self.offending_job.is_featured)

    def test_admin_resolve_user_suspended(self):
        """Super Admin resolves report with USER_SUSPENDED action suspending offending account"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('reports:admin-report-resolve', kwargs={'pk': self.report_user.id})
        data = {
            'status': Report.Status.ACTION_TAKEN,
            'action_taken': Report.ActionTaken.USER_SUSPENDED,
            'admin_notes': 'Account confirmed fake. Suspending user.'
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user was suspended
        self.offending_company.refresh_from_db()
        self.assertTrue(self.offending_company.is_suspended)

    def test_admin_resolve_dismissed(self):
        """Super Admin dismisses report with no violation"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('reports:admin-report-resolve', kwargs={'pk': self.report_job.id})
        data = {
            'status': Report.Status.DISMISSED,
            'action_taken': Report.ActionTaken.DISMISSED,
            'admin_notes': 'Investigated and no violation found.'
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.report_job.refresh_from_db()
        self.assertEqual(self.report_job.status, Report.Status.DISMISSED)

    def test_non_admin_cannot_access_moderation(self):
        """Regular user receives 403 Forbidden on admin moderation console"""
        self.client.force_authenticate(user=self.reporter_user)
        url = reverse('reports:admin-reports-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
