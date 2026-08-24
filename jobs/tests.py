from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job


class JobManagementTestsBase(APITestCase):
    """Base setup for Job tests"""
    def setUp(self):
        # Create Category
        self.tech_cat = Category.objects.create(
            name="Technology & IT",
            description="Tech jobs"
        )
        self.design_cat = Category.objects.create(
            name="Design & Creative",
            description="Design jobs"
        )

        # Create Company User A (Verified)
        self.company_a = User.objects.create_user(
            email="companyA@example.com",
            password="SecurePassword123!",
            first_name="TechCorp",
            last_name="Inc",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )

        # Create Company User B (Verified)
        self.company_b = User.objects.create_user(
            email="companyB@example.com",
            password="SecurePassword123!",
            first_name="DesignStudio",
            last_name="LLC",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )

        # Create Unverified Company
        self.unverified_company = User.objects.create_user(
            email="unverified@example.com",
            password="SecurePassword123!",
            first_name="Unverified",
            last_name="Corp",
            role=User.Role.COMPANY,
            is_verified=False,
            is_active=True
        )

        # Create Applicant User
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Doe",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )

        # Create Super Admin User
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="SecurePassword123!",
            first_name="Admin",
            last_name="User"
        )

        # Create Sample Jobs for Company A
        self.job_a1 = Job.objects.create(
            company=self.company_a,
            category=self.tech_cat,
            title="Senior Python Backend Developer",
            description="We are seeking an experienced Python/Django engineer.",
            requirements="5+ years Python, Django REST framework, PostgreSQL, Docker.",
            responsibilities="Design APIs, write scalable backend code, mentor juniors.",
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.REMOTE,
            location="Remote",
            experience_level=Job.ExperienceLevel.SENIOR,
            min_salary=80000,
            max_salary=120000,
            salary_currency="USD",
            status=Job.Status.PUBLISHED,
            is_featured=True,
            deadline=timezone.now().date() + timedelta(days=30)
        )

        self.job_a_draft = Job.objects.create(
            company=self.company_a,
            category=self.tech_cat,
            title="Junior DevOps Engineer (Draft)",
            description="Internal draft for upcoming role.",
            requirements="Linux, CI/CD.",
            location="New York, USA",
            status=Job.Status.DRAFT
        )

        # Create Sample Job for Company B
        self.job_b1 = Job.objects.create(
            company=self.company_b,
            category=self.design_cat,
            title="Lead UI/UX Product Designer",
            description="Lead design across web and mobile platforms.",
            requirements="Figma, Design Systems, User Research.",
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.HYBRID,
            location="London, UK",
            experience_level=Job.ExperienceLevel.LEAD,
            min_salary=70000,
            max_salary=95000,
            status=Job.Status.PUBLISHED
        )


class PublicJobListingTests(JobManagementTestsBase):
    """Tests for public job discovery, filters, search, and details"""

    def test_list_published_jobs_guest(self):
        """Unauthenticated guests can view published jobs; drafts are hidden"""
        url = reverse('jobs:public-job-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # 2 published jobs (job_a1, job_b1), 1 draft hidden
        self.assertEqual(response.data['count'], 2)

    def test_search_jobs_by_keyword(self):
        """Keyword search finds matches in title and requirements"""
        url = reverse('jobs:public-job-list') + "?q=Python"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.job_a1.title)

    def test_filter_jobs_by_category(self):
        """Filter jobs by category slug"""
        url = reverse('jobs:public-job-list') + f"?category={self.design_cat.slug}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.job_b1.title)

    def test_filter_jobs_by_workplace_type(self):
        """Filter jobs by workplace type (remote)"""
        url = reverse('jobs:public-job-list') + "?workplace_type=remote"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['workplace_type'], 'remote')

    def test_get_job_detail_and_increments_views(self):
        """Viewing job detail increments views_count"""
        initial_views = self.job_a1.views_count
        url = reverse('jobs:public-job-detail', kwargs={'slug_or_id': self.job_a1.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['title'], self.job_a1.title)
        
        self.job_a1.refresh_from_db()
        self.assertEqual(self.job_a1.views_count, initial_views + 1)

    def test_categories_list_with_job_counts(self):
        """Category listing includes annotated count of active published jobs"""
        url = reverse('jobs:category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        categories = response.data['data']
        tech = next(c for c in categories if c['slug'] == self.tech_cat.slug)
        self.assertEqual(tech['job_count'], 1)  # 1 published, 1 draft excluded

    def test_featured_jobs_endpoint(self):
        """Featured jobs endpoint returns only featured jobs"""
        url = reverse('jobs:featured-jobs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['data'][0]['id'], str(self.job_a1.id))


class CompanyJobManagementTests(JobManagementTestsBase):
    """Tests for company job posting, updating, deleting, and status toggling"""

    def test_verified_company_can_create_job(self):
        """Verified company creates new job successfully"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-create')
        data = {
            "category_id": str(self.tech_cat.id),
            "title": "Full Stack Engineer (React & Django)",
            "description": "Looking for a full stack engineer to join our fast-growing startup.",
            "requirements": "Strong experience with Django REST Framework and React / TypeScript.",
            "responsibilities": "Build new features and maintain code quality.",
            "job_type": "full_time",
            "workplace_type": "remote",
            "location": "Global / Remote",
            "experience_level": "mid",
            "min_salary": 60000,
            "max_salary": 90000,
            "status": "published",
            "deadline": (timezone.now().date() + timedelta(days=45)).isoformat()
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['company']['email'], self.company_a.email)

    def test_unauthenticated_cannot_create_job(self):
        """Unauthenticated user gets HTTP 401 Unauthorized when trying to create a job"""
        url = reverse('jobs:company-job-create')
        data = {
            "category_id": str(self.tech_cat.id),
            "title": "Unauthorized Job",
            "description": "This should be blocked.",
            "requirements": "None",
            "location": "Remote"
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unverified_company_cannot_create_job(self):
        """Unverified company gets HTTP 403 Forbidden"""
        self.client.force_authenticate(user=self.unverified_company)
        url = reverse('jobs:company-job-create')
        data = {
            "category_id": str(self.tech_cat.id),
            "title": "Unverified Job",
            "description": "Must verify email first.",
            "requirements": "None",
            "location": "Remote"
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_salary_validation_min_greater_than_max(self):
        """Validation fails if min_salary > max_salary"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-create')
        data = {
            "category_id": str(self.tech_cat.id),
            "title": "Invalid Salary Job",
            "description": "Description is long enough here.",
            "requirements": "Requirements are long enough here.",
            "location": "Remote",
            "min_salary": 100000,
            "max_salary": 50000
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('max_salary', response.data['errors'])

    def test_deadline_in_past_rejected(self):
        """Validation fails if deadline is in the past"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-create')
        data = {
            "category_id": str(self.tech_cat.id),
            "title": "Expired Deadline Job",
            "description": "Description is long enough here.",
            "requirements": "Requirements are long enough here.",
            "location": "Remote",
            "deadline": (timezone.now().date() - timedelta(days=2)).isoformat()
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('deadline', response.data['errors'])

    def test_company_can_view_my_jobs_including_drafts(self):
        """Company sees all their own jobs (published + drafts)"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-my-jobs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # job_a1 + job_a_draft

    def test_company_can_update_own_job(self):
        """Company can update their own job posting"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-detail', kwargs={'pk': self.job_a1.id})
        data = {"title": "Lead Principal Python Engineer", "max_salary": 140000}
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['title'], "Lead Principal Python Engineer")

    def test_company_cannot_edit_other_company_job(self):
        """Company B cannot edit Company A's job (HTTP 403 / 404)"""
        self.client.force_authenticate(user=self.company_b)
        url = reverse('jobs:company-job-detail', kwargs={'pk': self.job_a1.id})
        data = {"title": "Malicious Modification"}
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_can_toggle_job_status(self):
        """Company toggles job between PUBLISHED and CLOSED"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-toggle-status', kwargs={'pk': self.job_a1.id})
        
        # Toggle from PUBLISHED to CLOSED
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'closed')

        # Toggle from CLOSED back to PUBLISHED
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'published')

    def test_company_can_delete_own_job(self):
        """Company can delete their own job posting"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('jobs:company-job-detail', kwargs={'pk': self.job_a_draft.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Job.objects.filter(id=self.job_a_draft.id).exists())


class AdminJobModerationTests(JobManagementTestsBase):
    """Tests for super admin moderation of jobs and categories"""

    def test_admin_can_view_all_jobs(self):
        """Super admin can view all platform jobs across all companies"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('jobs:admin-all-jobs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)  # all jobs

    def test_admin_can_toggle_featured_job(self):
        """Super admin can promote a job to featured"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('jobs:admin-job-toggle-feature', kwargs={'pk': self.job_b1.id})
        self.assertFalse(self.job_b1.is_featured)
        
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['is_featured'])

    def test_admin_can_create_new_category(self):
        """Super admin creates new job category"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('jobs:admin-category-create')
        data = {"name": "Data Science & AI", "description": "Machine Learning and AI roles"}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['name'], "Data Science & AI")
        self.assertEqual(response.data['data']['slug'], "data-science-ai")

    def test_admin_can_delete_job(self):
        """Super admin can remove violating job posting"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('jobs:admin-job-manage', kwargs={'pk': self.job_b1.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Job.objects.filter(id=self.job_b1.id).exists())
