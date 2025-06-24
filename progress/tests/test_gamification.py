
from django.test import TestCase
from ..models import Category, Task, Achievement 
from ..gamification import GamificationEngine

from django.contrib.auth import get_user_model

User = get_user_model()

class GamificationEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            xp_multiplier=1.0
        )
        self.engine = GamificationEngine(self.user)

    def test_xp_calculation_by_difficulty(self):
        # Test different difficulty levels
        easy_task = Task.objects.create(
            user=self.user,
            title='Easy Task',
            category=self.category,
            difficulty='easy'
        )
        
        medium_task = Task.objects.create(
            user=self.user,
            title='Medium Task',
            category=self.category,
            difficulty='medium'
        )
        
        hard_task = Task.objects.create(
            user=self.user,
            title='Hard Task',
            category=self.category,
            difficulty='hard'
        )
        
        easy_xp = self.engine.calculate_task_xp(easy_task)
        medium_xp = self.engine.calculate_task_xp(medium_task)
        hard_xp = self.engine.calculate_task_xp(hard_task)
        
        self.assertTrue(easy_xp < medium_xp < hard_xp)
        self.assertEqual(easy_xp, 10)
        self.assertEqual(medium_xp, 25)
        self.assertEqual(hard_xp, 50)

    def test_category_multiplier(self):
        # Create category with 2x multiplier
        bonus_category = Category.objects.create(
            name='Bonus Category',
            xp_multiplier=2.0
        )
        
        regular_task = Task.objects.create(
            user=self.user,
            title='Regular Task',
            category=self.category,
            difficulty='medium'
        )
        
        bonus_task = Task.objects.create(
            user=self.user,
            title='Bonus Task',
            category=bonus_category,
            difficulty='medium'
        )
        
        regular_xp = self.engine.calculate_task_xp(regular_task)
        bonus_xp = self.engine.calculate_task_xp(bonus_task)
        
        self.assertEqual(bonus_xp, regular_xp * 2)

    def test_achievement_checking(self):
        # Create a simple achievement
        achievement = Achievement.objects.create(
            name='First Task',
            description='Complete your first task',
            achievement_type='task_count',
            threshold=1,
            xp_reward=50
        )
        
        # Complete a task
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category
        )
        
        self.engine.award_task_xp(task)
        
        # Check if achievement was unlocked
        unlocked = self.user.achievements.filter(achievement=achievement).exists()
        self.assertTrue(unlocked)