from django.core.management.base import BaseCommand
from progress.models import Category

class Command(BaseCommand):
    help = 'Create default categories for the task management system'

    def handle(self, *args, **options):
        categories_data = [
            {
                'name': 'Work',
                'description': 'Professional and career-related tasks',
                'color': '#007bff',
                'xp_multiplier': 1.2
            },
            {
                'name': 'Personal',
                'description': 'Personal development and life tasks',
                'color': '#28a745',
                'xp_multiplier': 1.0
            },
            {
                'name': 'Health & Fitness',
                'description': 'Exercise, nutrition, and wellness tasks',
                'color': '#dc3545',
                'xp_multiplier': 1.3
            },
            {
                'name': 'Learning',
                'description': 'Education, courses, and skill development',
                'color': '#ffc107',
                'xp_multiplier': 1.4
            },
            {
                'name': 'Social',
                'description': 'Family, friends, and social activities',
                'color': '#17a2b8',
                'xp_multiplier': 1.0
            },
            {
                'name': 'Home',
                'description': 'Household chores and maintenance',
                'color': '#6f42c1',
                'xp_multiplier': 0.9
            },
            {
                'name': 'Finance',
                'description': 'Money management and financial planning',
                'color': '#fd7e14',
                'xp_multiplier': 1.1
            },
            {
                'name': 'Creative',
                'description': 'Art, writing, music, and creative projects',
                'color': '#e83e8c',
                'xp_multiplier': 1.2
            }
        ]

        created_count = 0
        for category_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created category: {category.name}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} categories')
        )
