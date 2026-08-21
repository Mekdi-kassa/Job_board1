from django.core.management.base import BaseCommand
from jobs.models import Category


class Command(BaseCommand):
    help = 'Seed initial job categories'

    def handle(self, *args, **kwargs):
        categories = [
            {'name': 'Technology & IT', 'icon': 'code', 'description': 'Software engineering, web development, DevOps, AI, cybersecurity'},
            {'name': 'Finance & Accounting', 'icon': 'chart-line', 'description': 'Banking, financial analysis, accounting, investment'},
            {'name': 'Healthcare & Medical', 'icon': 'heart-pulse', 'description': 'Nursing, doctors, medical research, healthcare management'},
            {'name': 'Design & Creative', 'icon': 'palette', 'description': 'UI/UX design, graphic design, animation, multimedia'},
            {'name': 'Marketing & Sales', 'icon': 'bullhorn', 'description': 'Digital marketing, SEO, social media, sales development'},
            {'name': 'Customer Support', 'icon': 'headset', 'description': 'Customer service, client success, help desk'},
            {'name': 'Education & Teaching', 'icon': 'graduation-cap', 'description': 'Tutoring, classroom teaching, curriculum development'},
            {'name': 'Engineering & Construction', 'icon': 'gear', 'description': 'Civil, mechanical, electrical, structural engineering'},
            {'name': 'Human Resources', 'icon': 'users', 'description': 'Talent acquisition, HR management, employee relations'},
            {'name': 'Writing & Content', 'icon': 'pen-nib', 'description': 'Copywriting, technical writing, journalism, translation'},
        ]

        created_count = 0
        for cat_data in categories:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'description': cat_data['description'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} new job categories.'))
