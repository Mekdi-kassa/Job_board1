import io
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from applications.models import Application


class ApplicationsTestBase(APITestCase):
    """Base test setup for Job Applications"""
    def setUp(self):
        # Create Category
        self.category = Category.objects.create(
            name="Technology & IT",
            slug="technology-it",
            description="Tech jobs"
        )

        # Create Company A
        self.company_a = User.objects.create_user(
            email="companya@example.com",
            password="SecurePassword123!",
            first_name="TechCorp",
            last_name="Inc",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )

        # Create Company B
        self.company_b = User.objects.create_user(
            email="companyb@example.com",
            password="SecurePassword123!",
            first_name="StartupHub",
            last_name="LLC",
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

        # Create Super Admin
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="SecurePassword123!",
            first_name="Super",
            last_name="Admin"
        )

        # Create Published Job for Company A
        self.job_a = Job.objects.create(
            company=self.company_a,
            category=self.category,
            title="Senior Python Backend Developer",
            description="We are seeking an experienced Python engineer.",
            requirements="Django, PostgreSQL, Docker.",
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.REMOTE,
            location="Remote",
            min_salary=80000,
            max_salary=120000,
            status=Job.Status.PUBLISHED,
            deadline=timezone.now().date() + timedelta(days=30)
        )

        # Create Closed Job for Company A
        self.closed_job = Job.objects.create(
            company=self.company_a,
            category=self.category,
            title="Closed Python Role",
            description="Expired position.",
            requirements="Django.",
            location="Remote",
            status=Job.Status.CLOSED
        )

        # Create a sample fake PDF resume
        self.fake_pdf = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4 sample resume content for testing",
            content_type="application/pdf"
        )


class JobApplicationSubmitTests(ApplicationsTestBase):
    """Tests for applicant submitting applications to jobs"""

    def test_apply_with_resume_file_success(self):
        """Applicant applies successfully with a valid PDF resume file"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        
        pdf_file = SimpleUploadedFile("my_resume.pdf", b"%PDF-1.4 resume text", content_type="application/pdf")
        data = {
            'resume': pdf_file,
            'cover_letter': 'I am very excited about this role.'
        }
        response = self.client.post(url, data=data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify job application count incremented
        self.job_a.refresh_from_db()
        self.assertEqual(self.job_a.applications_count, 1)

    def test_apply_with_resume_url_success(self):
        """Applicant applies with external resume URL link"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        
        data = {
            'resume_url': 'https://linkedin.com/in/alicesmith-resume',
            'cover_letter': 'Please check my LinkedIn portfolio link.'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

    def test_apply_missing_both_file_and_url_fails(self):
        """Application rejected if neither resume file nor URL is provided"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        data = {'cover_letter': 'I have no resume attached.'}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_application_rejected(self):
        """Applicant cannot apply twice to the same job"""
        Application.objects.create(
            job=self.job_a,
            applicant=self.applicant_1,
            resume_url='https://example.com/resume.pdf'
        )

        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        data = {'resume_url': 'https://example.com/resume2.pdf'}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already submitted an application', str(response.data['errors']))

    def test_cannot_apply_to_own_job_posting(self):
        """Company user cannot apply to their own job posting"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        data = {'resume_url': 'https://example.com/resume.pdf'}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cannot apply to your own job', str(response.data['errors']))

    def test_cannot_apply_to_closed_job(self):
        """Application rejected if job is closed"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:apply-job', kwargs={'job_id': self.closed_job.id})
        data = {'resume_url': 'https://example.com/resume.pdf'}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_user_cannot_apply(self):
        """Unauthenticated guests receive HTTP 401 Unauthorized"""
        url = reverse('applications:apply-job', kwargs={'job_id': self.job_a.id})
        data = {'resume_url': 'https://example.com/resume.pdf'}
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ApplicantTrackingTests(ApplicationsTestBase):
    """Tests for applicant tracking and withdrawing their applications"""

    def setUp(self):
        super().setUp()
        self.app_1 = Application.objects.create(
            job=self.job_a,
            applicant=self.applicant_1,
            resume_url='https://example.com/resume1.pdf',
            status=Application.Status.PENDING
        )

    def test_applicant_can_list_my_applications(self):
        """Applicant views all their submitted applications"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:my-applications-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.app_1.id))

    def test_applicant_can_view_single_application_detail(self):
        """Applicant views detailed progress of an application"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:my-application-detail', kwargs={'pk': self.app_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'pending')

    def test_applicant_cannot_view_other_applicant_detail(self):
        """Applicant 2 cannot view Applicant 1's application"""
        self.client.force_authenticate(user=self.applicant_2)
        url = reverse('applications:my-application-detail', kwargs={'pk': self.app_1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_applicant_can_withdraw_application(self):
        """Applicant withdraws their pending application"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('applications:my-application-withdraw', kwargs={'pk': self.app_1.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'withdrawn')
        
        self.app_1.refresh_from_db()
        self.assertEqual(self.app_1.status, Application.Status.WITHDRAWN)


class CompanyCandidateReviewPipelineTests(ApplicationsTestBase):
    """Tests for employer reviewing applicants and updating hiring stages"""

    def setUp(self):
        super().setUp()
        self.app_alice = Application.objects.create(
            job=self.job_a,
            applicant=self.applicant_1,
            resume_url='https://example.com/alice-resume.pdf',
            cover_letter='Alice cover letter',
            status=Application.Status.PENDING
        )
        self.app_bob = Application.objects.create(
            job=self.job_a,
            applicant=self.applicant_2,
            resume_url='https://example.com/bob-resume.pdf',
            cover_letter='Bob cover letter',
            status=Application.Status.SHORTLISTED,
            rating=5
        )

    def test_company_can_list_candidates_for_job(self):
        """Company lists all candidates who applied to their job"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('applications:company-job-candidates', kwargs={'job_id': self.job_a.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_company_can_filter_candidates_by_rating(self):
        """Company filters candidates with minimum rating 4"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('applications:company-job-candidates', kwargs={'job_id': self.job_a.id}) + "?min_rating=4"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['applicant']['email'], self.applicant_2.email)

    def test_company_can_view_full_candidate_detail(self):
        """Company views candidate cover letter, resume, and profile"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('applications:company-candidate-detail', kwargs={'pk': self.app_alice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['applicant']['email'], self.applicant_1.email)

    def test_company_can_update_candidate_status_and_rating(self):
        """Company advances candidate to INTERVIEWED and adds rating & notes"""
        self.client.force_authenticate(user=self.company_a)
        url = reverse('applications:company-candidate-status-update', kwargs={'pk': self.app_alice.id})
        data = {
            'status': 'interviewed',
            'rating': 4,
            'company_notes': 'Great communication skills in initial screening.'
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'interviewed')
        self.assertEqual(response.data['data']['rating'], 4)
        self.assertEqual(response.data['data']['company_notes'], 'Great communication skills in initial screening.')

    def test_other_company_cannot_view_or_edit_candidates(self):
        """Company B cannot view or edit candidates for Company A's job"""
        self.client.force_authenticate(user=self.company_b)
        url = reverse('applications:company-candidate-detail', kwargs={'pk': self.app_alice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        status_url = reverse('applications:company-candidate-status-update', kwargs={'pk': self.app_alice.id})
        response = self.client.patch(status_url, data={'status': 'rejected'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminApplicationsModerationTests(ApplicationsTestBase):
    """Tests for super admin moderating applications"""

    def test_admin_can_view_all_applications(self):
        """Super Admin views all platform applications"""
        Application.objects.create(
            job=self.job_a,
            applicant=self.applicant_1,
            resume_url='https://example.com/resume1.pdf'
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('applications:admin-all-applications')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
