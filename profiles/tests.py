from datetime import date
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from profiles.models import CompanyProfile, ApplicantProfile, Skill, WorkExperience, Education


class ProfilesTestBase(APITestCase):
    """Base setup for Profile tests"""
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
            first_name="TechFlow",
            last_name="HQ",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )
        self.company_profile = self.company_user.company_profile
        self.company_profile.company_name = 'TechFlow Inc'
        self.company_profile.tagline = 'Building next-gen developer tools'
        self.company_profile.about = 'We are an innovative tech company.'
        self.company_profile.industry = self.category
        self.company_profile.company_size = CompanyProfile.CompanySize.SIZE_11_50
        self.company_profile.headquarters = 'San Francisco, CA'
        self.company_profile.website = 'https://techflow.io'
        self.company_profile.save()

        # Create Published Job for Company
        self.job = Job.objects.create(
            company=self.company_user,
            category=self.category,
            title="Senior Python Backend Developer",
            description="Exciting Python role.",
            requirements="Python & Django.",
            location="Remote",
            status=Job.Status.PUBLISHED
        )

        # Create Applicant 1
        self.applicant_1 = User.objects.create_user(
            email="applicant1@example.com",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="Smith",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )
        self.app_profile_1 = self.applicant_1.applicant_profile
        self.app_profile_1.headline = 'Senior Full Stack Developer'
        self.app_profile_1.bio = 'Passionate about scalable systems.'
        self.app_profile_1.location = 'New York, NY'
        self.app_profile_1.expected_salary = 110000
        self.app_profile_1.save()

        # Create Applicant 2
        self.applicant_2 = User.objects.create_user(
            email="applicant2@example.com",
            password="SecurePassword123!",
            first_name="Bob",
            last_name="Jones",
            role=User.Role.APPLICANT,
            is_verified=True,
            is_active=True
        )
        self.app_profile_2 = self.applicant_2.applicant_profile

        # Create Skills
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_django = Skill.objects.create(name="Django")
        self.skill_react = Skill.objects.create(name="React")


class CompanyProfileAPITests(ProfilesTestBase):
    """Tests for company profile management and public showcase"""

    def test_get_my_company_profile(self):
        """Company gets their own profile details"""
        self.client.force_authenticate(user=self.company_user)
        url = reverse('profiles:company-my-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['company_name'], 'TechFlow Inc')
        self.assertEqual(response.data['data']['active_jobs_count'], 1)

    def test_update_company_profile(self):
        """Company updates their tagline and headquarters"""
        self.client.force_authenticate(user=self.company_user)
        url = reverse('profiles:company-my-profile')
        data = {
            'tagline': 'Empowering engineers worldwide',
            'headquarters': 'Austin, TX'
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['tagline'], 'Empowering engineers worldwide')
        self.assertEqual(response.data['data']['headquarters'], 'Austin, TX')

    def test_public_companies_directory(self):
        """Guests can browse public directory of companies"""
        url = reverse('profiles:company-public-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['company_name'], 'TechFlow Inc')

    def test_public_company_showcase_detail_with_jobs(self):
        """Guests can view company public showcase with their active jobs"""
        url = reverse('profiles:company-public-detail', kwargs={'slug_or_id': self.company_profile.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['company_name'], 'TechFlow Inc')
        self.assertEqual(len(response.data['data']['active_jobs']), 1)
        self.assertEqual(response.data['data']['active_jobs'][0]['title'], self.job.title)


class ApplicantProfileAPITests(ProfilesTestBase):
    """Tests for applicant profile, skills, experience, and education"""

    def test_get_my_applicant_profile(self):
        """Applicant gets their own profile"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-my-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['headline'], 'Senior Full Stack Developer')

    def test_update_applicant_profile_and_skills(self):
        """Applicant updates headline and attaches skills"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-my-profile')
        data = {
            'headline': 'Lead Cloud Architect',
            'skill_ids': [str(self.skill_python.id), str(self.skill_django.id)]
        }
        response = self.client.patch(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['headline'], 'Lead Cloud Architect')
        self.assertEqual(len(response.data['data']['skills']), 2)

    def test_add_work_experience(self):
        """Applicant adds work experience entry"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-experience-list-create')
        data = {
            'company_name': 'Acme Corp',
            'position': 'Backend Engineer',
            'location': 'Remote',
            'start_date': '2022-01-15',
            'end_date': '2024-05-30',
            'is_current': False,
            'description': 'Built microservices using Django REST framework and AWS.'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['company_name'], 'Acme Corp')
        self.assertEqual(WorkExperience.objects.filter(profile=self.app_profile_1).count(), 1)

    def test_delete_work_experience(self):
        """Applicant deletes work experience entry"""
        exp = WorkExperience.objects.create(
            profile=self.app_profile_1,
            company_name='Old Company',
            position='Junior Dev',
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31)
        )
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-experience-detail', kwargs={'pk': exp.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkExperience.objects.filter(id=exp.id).exists())

    def test_other_applicant_cannot_delete_experience(self):
        """Applicant 2 cannot delete Applicant 1's work experience"""
        exp = WorkExperience.objects.create(
            profile=self.app_profile_1,
            company_name='Protected Company',
            position='Engineer',
            start_date=date(2021, 1, 1),
            is_current=True
        )
        self.client.force_authenticate(user=self.applicant_2)
        url = reverse('profiles:applicant-experience-detail', kwargs={'pk': exp.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_education_entry(self):
        """Applicant adds education entry"""
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-education-list-create')
        data = {
            'institution': 'University of California, Berkeley',
            'degree': 'Bachelor of Science',
            'field_of_study': 'Computer Science',
            'start_year': 2017,
            'end_year': 2021,
            'grade_or_gpa': '3.9'
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['institution'], 'University of California, Berkeley')
        self.assertEqual(Education.objects.filter(profile=self.app_profile_1).count(), 1)

    def test_delete_education_entry(self):
        """Applicant deletes education entry"""
        edu = Education.objects.create(
            profile=self.app_profile_1,
            institution='MIT',
            degree='M.S.',
            field_of_study='AI',
            start_year=2021,
            end_year=2023
        )
        self.client.force_authenticate(user=self.applicant_1)
        url = reverse('profiles:applicant-education-detail', kwargs={'pk': edu.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Education.objects.filter(id=edu.id).exists())


class MarketplaceAPITests(ProfilesTestBase):
    """Tests for Community and Talent Marketplace endpoints"""

    def setUp(self):
        super().setUp()
        # Associate skills with applicant 1
        self.app_profile_1.skills.add(self.skill_python, self.skill_django)
        self.client.force_authenticate(user=self.applicant_1)

    def test_unauthenticated_marketplace_access_denied(self):
        """Unauthenticated requests are rejected with 401 Unauthorized"""
        self.client.force_authenticate(user=None)
        url = reverse('profiles:marketplace-overview')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_marketplace_overview(self):
        """Get marketplace overview statistics and featured listings"""
        url = reverse('profiles:marketplace-overview')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('metrics', response.data['data'])
        self.assertIn('featured_talents', response.data['data'])
        self.assertIn('featured_companies', response.data['data'])

    def test_talent_marketplace_list(self):
        """List candidates open to work in the marketplace"""
        url = reverse('profiles:talent-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)

    def test_talent_marketplace_filter_by_skill(self):
        """Filter talent marketplace by specific skill"""
        url = reverse('profiles:talent-list') + '?skill=Python'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['email'], 'applicant1@example.com')

    def test_talent_showcase_detail(self):
        """Public view of candidate detailed profile"""
        url = reverse('profiles:talent-detail', kwargs={'user_id_or_profile_id': str(self.applicant_1.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['headline'], 'Senior Full Stack Developer')
