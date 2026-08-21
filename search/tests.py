from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from user.models import User
from jobs.models import Category, Job
from profiles.models import CompanyProfile, Skill


class SearchEngineAPITests(APITestCase):
    """Automated tests for Unified Search, Autocomplete, Facets, and Trending Discovery"""

    def setUp(self):
        # Create Categories
        self.tech_cat = Category.objects.create(
            name="Technology & IT",
            description="Software & IT jobs"
        )
        self.finance_cat = Category.objects.create(
            name="Finance & Banking",
            description="Financial roles"
        )

        # Create Company Users
        self.company_user = User.objects.create_user(
            email="techcorp@example.com",
            password="SecurePassword123!",
            first_name="TechCorp",
            last_name="Inc",
            role=User.Role.COMPANY,
            is_verified=True,
            is_active=True
        )
        self.company_profile = self.company_user.company_profile
        self.company_profile.company_name = "TechCorp Solutions"
        self.company_profile.is_verified_badge = True
        self.company_profile.save()

        # Create Skills
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_django = Skill.objects.create(name="Django")

        # Create Published Job 1 (Python, Remote, Senior, $100k-$130k, Featured)
        self.job_python = Job.objects.create(
            company=self.company_user,
            category=self.tech_cat,
            title="Senior Python Django Engineer",
            description="Build cloud backends using Django REST framework.",
            requirements="Python, Django, PostgreSQL, Docker.",
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.REMOTE,
            location="Remote / Global",
            experience_level=Job.ExperienceLevel.SENIOR,
            min_salary=100000,
            max_salary=130000,
            status=Job.Status.PUBLISHED,
            is_featured=True,
            views_count=50,
            deadline=timezone.now().date() + timedelta(days=30)
        )

        # Create Published Job 2 (React, Hybrid, Mid, $70k-$90k)
        self.job_react = Job.objects.create(
            company=self.company_user,
            category=self.tech_cat,
            title="Frontend React Developer",
            description="Build interactive UI with React and TypeScript.",
            requirements="React, TypeScript, CSS3.",
            job_type=Job.JobType.FULL_TIME,
            workplace_type=Job.WorkplaceType.HYBRID,
            location="New York, NY",
            experience_level=Job.ExperienceLevel.MID,
            min_salary=70000,
            max_salary=90000,
            status=Job.Status.PUBLISHED,
            views_count=20,
            deadline=timezone.now().date() + timedelta(days=20)
        )

        # Create Draft Job (Must not appear in search)
        self.job_draft = Job.objects.create(
            company=self.company_user,
            category=self.tech_cat,
            title="Hidden Internal Python Draft",
            description="Draft role.",
            status=Job.Status.DRAFT
        )

    def test_search_by_keyword_python(self):
        """Search by keyword 'Python' matches Python job and excludes React job and drafts"""
        url = reverse('search:unified-search') + "?q=Python"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.job_python.title)

    def test_search_filter_by_workplace_type_remote(self):
        """Filter by remote workplace type"""
        url = reverse('search:unified-search') + "?workplace_type=remote"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['workplace_type'], 'remote')

    def test_search_filter_by_salary_range(self):
        """Filter by minimum salary >= 95,000"""
        url = reverse('search:unified-search') + "?min_salary=95000"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], self.job_python.title)

    def test_search_ordering_by_salary_high_to_low(self):
        """Ordering by salary_high_to_low returns higher paying job first"""
        url = reverse('search:unified-search') + "?ordering=salary_high_to_low"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['title'], self.job_python.title)
        self.assertEqual(response.data['results'][1]['title'], self.job_react.title)

    def test_autocomplete_suggestions_query_py(self):
        """Autocomplete for 'py' returns matching jobs, companies, categories, and skills"""
        url = reverse('search:search-suggestions') + "?q=py"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertTrue(any("Python" in j['title'] for j in data['jobs']))
        self.assertTrue(any("Python" in s['name'] for s in data['skills']))

    def test_autocomplete_short_query_returns_empty(self):
        """Short query (< 2 characters) returns empty lists"""
        url = reverse('search:search-suggestions') + "?q=p"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(len(data['jobs']), 0)
        self.assertEqual(len(data['skills']), 0)

    def test_search_facets_aggregation(self):
        """Search facets returns accurate aggregated counts"""
        url = reverse('search:search-facets')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        facets = response.data['facets']
        self.assertEqual(facets['workplace_types'].get('remote'), 1)
        self.assertEqual(facets['workplace_types'].get('hybrid'), 1)
        self.assertEqual(facets['job_types'].get('full_time'), 2)

    def test_trending_discovery_hub(self):
        """Trending endpoint returns popular categories, featured jobs, and trending keywords"""
        url = reverse('search:trending-discovery')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertIn('top_categories', data)
        self.assertIn('featured_jobs', data)
        self.assertIn('trending_keywords', data)
        self.assertEqual(len(data['featured_jobs']), 1)
        self.assertEqual(data['featured_jobs'][0]['id'], str(self.job_python.id))
