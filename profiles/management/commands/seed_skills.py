from django.core.management.base import BaseCommand
from profiles.models import Skill


class Command(BaseCommand):
    help = 'Seed initial professional skills'

    def handle(self, *args, **kwargs):
        skills = [
            'Python', 'Django', 'Django REST Framework', 'FastAPI', 'JavaScript',
            'TypeScript', 'React', 'Next.js', 'Vue.js', 'Node.js', 'PostgreSQL',
            'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes', 'AWS', 'GCP',
            'Azure', 'CI/CD', 'Git', 'Linux', 'GraphQL', 'REST APIs', 'HTML5',
            'CSS3', 'Tailwind CSS', 'Figma', 'UI/UX Design', 'Machine Learning',
            'Data Science', 'Pandas', 'PyTorch', 'TensorFlow', 'DevOps', 'Agile'
        ]

        created_count = 0
        for skill_name in skills:
            _, created = Skill.objects.get_or_create(name=skill_name)
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {created_count} skills.'))
