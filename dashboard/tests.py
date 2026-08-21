from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from applications.models import Application
from profiles.models import Skill


class DashboardAPITestsBase(APITestCase):
    """Base setup for Dashboard & Analytics tests"""
    def setUp(self):
        # Create Category
        self.tech_cat = Category.objects.create(
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

        # Create Applicant User
        self.applicant_user = User.objects.create_user(
            email="applicant@example.com",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Developer",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Attach skills to applicant profile
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_django = Skill.objects.create(name="Django")
        self.applicant_user.applicant_profile.skills.add(self.skill_python, self.skill_django)

        # Create Super Admin
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="SecurePassword123!",
            first_name="Super",
            last_name="Admin"
        )

        # Create Company Jobs
        self.job_1 = Job.objects.create(
            company=self.company_user,
            category=self.tech_cat,
            title="Senior Python Backend Developer",
            description="Build scalable Django APIs.",
            requirements="Python & Django required.",
            status=Job.Status.PUBLISHED,
            views_count=100,
            deadline=timezone.now().date() + timedelta(days=30)
        )

        self.job_2 = Job.objects.create(
            company=self.company_user,
            category=self.tech_cat,
            title="Junior DevOps Engineer",
            description="Linux & Docker.",
            requirements="Docker, CI/CD.",
            status=Job.Status.PUBLISHED,
            views_count=40,
            deadline=timezone.now().date() + timedelta(days=30)
        )

        # Create Application
        self.app = Application.objects.create(
            job=self.job_1,
            applicant=self.applicant_user,
            resume_url="https://example.com/jane-resume.pdf",
            status=Application.Status.SHORTLISTED,
            rating=5
        )


class CompanyDashboardTests(DashboardAPITestsBase):
    """Tests for employer hiring dashboard"""

    def test_company_dashboard_metrics(self):
        """Company gets overview counts and pipeline metrics"""
        self.client.force_authenticate(user=self.company_user)
        url = reverse('dashboard:company-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        data = response.data['data']
        self.assertEqual(data['overview']['total_jobs'], 2)
        self.assertEqual(data['overview']['active_jobs'], 2)
        self.assertEqual(data['overview']['total_applications'], 1)
        self.assertEqual(data['overview']['total_job_views'], 140)

        # Pipeline
        self.assertEqual(data['pipeline']['shortlisted'], 1)
        self.assertEqual(data['pipeline']['pending'], 0)

        # Recent applicants
        self.assertEqual(len(data['recent_applicants']), 1)
        self.assertEqual(data['recent_applicants'][0]['applicant_email'], self.applicant_user.email)


class ApplicantDashboardTests(DashboardAPITestsBase):
    """Tests for job seeker application tracker and recommendations"""

    def test_applicant_dashboard_metrics_and_recommendations(self):
        """Applicant views tracker and skill-matched recommendations"""
        self.client.force_authenticate(user=self.applicant_user)
        url = reverse('dashboard:applicant-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        data = response.data['data']
        self.assertEqual(data['overview']['total_applications'], 1)
        self.assertEqual(data['overview']['shortlisted'], 1)

        # Recent applications
        self.assertEqual(len(data['recent_applications']), 1)
        self.assertEqual(data['recent_applications'][0]['job_title'], self.job_1.title)

        # Recommendations exclude already applied job_1 and recommend job_2
        self.assertTrue(any(j['id'] == self.job_2.id for j in data['recommended_jobs']))


class AdminDashboardAnalyticsTests(DashboardAPITestsBase):
    """Tests for super admin platform analytics"""

    def test_admin_dashboard_metrics(self):
        """Super Admin gets aggregated platform health metrics"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard:admin-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        data = response.data['data']
        self.assertEqual(data['user_metrics']['total_users'], 3)
        self.assertEqual(data['user_metrics']['applicants_count'], 1)
        self.assertEqual(data['user_metrics']['companies_count'], 1)
        self.assertEqual(data['job_metrics']['total_jobs'], 2)
        self.assertEqual(data['application_metrics']['total_applications'], 1)

    def test_non_admin_cannot_access_admin_dashboard(self):
        """Regular applicant/company is blocked from admin analytics"""
        self.client.force_authenticate(user=self.applicant_user)
        url = reverse('dashboard:admin-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_dashboard(self):
        """Unauthenticated guest receives 401 Unauthorized"""
        url = reverse('dashboard:company-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
