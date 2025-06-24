from django.core.management.base import BaseCommand
from progress.models import Achievement 

class Command(BaseCommand):
    help = 'Create default achievements for the gamification system'

    def handle(self, *args, **options):
        achievements_data = [
            # Task count achievements
            {
                'name': 'First Steps',
                'description': 'Complete your first task',
                'achievement_type': 'task_count',
                'icon': '🎯',
                'threshold': 1,
                'xp_reward': 25,
                'is_hidden': False
            },
            {
                'name': 'Getting Started',
                'description': 'Complete 10 tasks',
                'achievement_type': 'task_count',
                'icon': '📝',
                'threshold': 10,
                'xp_reward': 100,
                'is_hidden': False
            },
            {
                'name': 'Task Master',
                'description': 'Complete 50 tasks',
                'achievement_type': 'task_count',
                'icon': '⭐',
                'threshold': 50,
                'xp_reward': 250,
                'is_hidden': False
            },
            {
                'name': 'Productivity Legend',
                'description': 'Complete 100 tasks',
                'achievement_type': 'task_count',
                'icon': '🏆',
                'threshold': 100,
                'xp_reward': 500,
                'is_hidden': False
            },
            {
                'name': 'Task Conqueror',
                'description': 'Complete 500 tasks',
                'achievement_type': 'task_count',
                'icon': '👑',
                'threshold': 500,
                'xp_reward': 1000,
                'is_hidden': True
            },

            # Streak achievements
            {
                'name': 'Consistency',
                'description': 'Maintain a 3-day streak',
                'achievement_type': 'streak',
                'icon': '🔥',
                'threshold': 3,
                'xp_reward': 50,
                'is_hidden': False
            },
            {
                'name': 'Weekly Warrior',
                'description': 'Maintain a 7-day streak',
                'achievement_type': 'streak',
                'icon': '🌟',
                'threshold': 7,
                'xp_reward': 150,
                'is_hidden': False
            },
            {
                'name': 'Monthly Master',
                'description': 'Maintain a 30-day streak',
                'achievement_type': 'streak',
                'icon': '🎖️',
                'threshold': 30,
                'xp_reward': 500,
                'is_hidden': False
            },
            {
                'name': 'Unstoppable',
                'description': 'Maintain a 100-day streak',
                'achievement_type': 'streak',
                'icon': '💎',
                'threshold': 100,
                'xp_reward': 1500,
                'is_hidden': True
            },

            # Level achievements
            {
                'name': 'Level Up!',
                'description': 'Reach level 5',
                'achievement_type': 'level',
                'icon': '🆙',
                'threshold': 5,
                'xp_reward': 100,
                'is_hidden': False
            },
            {
                'name': 'Rising Star',
                'description': 'Reach level 10',
                'achievement_type': 'level',
                'icon': '🌠',
                'threshold': 10,
                'xp_reward': 250,
                'is_hidden': False
            },
            {
                'name': 'Expert Level',
                'description': 'Reach level 25',
                'achievement_type': 'level',
                'icon': '🎓',
                'threshold': 25,
                'xp_reward': 750,
                'is_hidden': False
            },
            {
                'name': 'Grandmaster',
                'description': 'Reach level 50',
                'achievement_type': 'level',
                'icon': '🧙‍♂️',
                'threshold': 50,
                'xp_reward': 2000,
                'is_hidden': True
            },

            # XP achievements
            {
                'name': 'First Thousand',
                'description': 'Earn 1,000 XP',
                'achievement_type': 'xp',
                'icon': '💰',
                'threshold': 1000,
                'xp_reward': 100,
                'is_hidden': False
            },
            {
                'name': 'XP Collector',
                'description': 'Earn 5,000 XP',
                'achievement_type': 'xp',
                'icon': '💎',
                'threshold': 5000,
                'xp_reward': 500,
                'is_hidden': False
            },
            {
                'name': 'XP Millionaire',
                'description': 'Earn 10,000 XP',
                'achievement_type': 'xp',
                'icon': '🏦',
                'threshold': 10000,
                'xp_reward': 1000,
                'is_hidden': True
            },

            # Category achievements
            {
                'name': 'Category Specialist',
                'description': 'Complete 25 tasks in any single category',
                'achievement_type': 'category',
                'icon': '🎯',
                'threshold': 25,
                'xp_reward': 200,
                'is_hidden': False
            },
            {
                'name': 'Category Expert',
                'description': 'Complete 50 tasks in any single category',
                'achievement_type': 'category',
                'icon': '🏅',
                'threshold': 50,
                'xp_reward': 400,
                'is_hidden': False
            },
            {
                'name': 'Category Master',
                'description': 'Complete 100 tasks in any single category',
                'achievement_type': 'category',
                'icon': '🎖️',
                'threshold': 100,
                'xp_reward': 800,
                'is_hidden': True
            },

            # Special achievements
            {
                'name': 'Night Owl',
                'description': 'Complete a task after 10 PM',
                'achievement_type': 'special',
                'icon': '🦉',
                'threshold': 1,
                'xp_reward': 50,
                'is_hidden': False
            },
            {
                'name': 'Early Bird',
                'description': 'Complete a task before 6 AM',
                'achievement_type': 'special',
                'icon': '🐦',
                'threshold': 1,
                'xp_reward': 50,
                'is_hidden': False
            },
            {
                'name': 'Speed Demon',
                'description': 'Complete 10 tasks in a single day',
                'achievement_type': 'special',
                'icon': '⚡',
                'threshold': 10,
                'xp_reward': 200,
                'is_hidden': False
            }
        ]

        created_count = 0
        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created achievement: {achievement.name}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} achievements')
        )