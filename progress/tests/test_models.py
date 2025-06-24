from django.test import TestCase
from ..models import Category, Task, XPLog, ProgressProfile 
from django.contrib.auth import get_user_model

User = get_user_model()

class TaskModelTest(TestCase):
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

    def test_task_creation(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='A test task',
            category=self.category,
            difficulty='medium'
        )
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.user, self.user)
        self.assertFalse(task.is_completed)

    def test_task_completion(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category,
            difficulty='easy'
        )
        
        # Complete the task
        result = task.complete_task()
        
        task.refresh_from_db()
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)
        self.assertTrue(result)

    def test_task_completion_awards_xp(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category,
            difficulty='medium'
        )
        
        # Complete the task
        task.complete_task()
        
        # Check XP was awarded
        xp_log = XPLog.objects.filter(user=self.user, task=task).first()
        self.assertIsNotNone(xp_log)
        self.assertEqual(xp_log.action, 'task_complete')
        self.assertTrue(xp_log.xp_earned > 0)

class ProgressProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = ProgressProfile.objects.create(user=self.user)

    def test_xp_level_calculation(self):
        # Test level 1 (0 XP)
        self.assertEqual(self.profile.calculate_xp_for_level(1), 0)
        
        # Test level 2 (100 XP)
        self.assertEqual(self.profile.calculate_xp_for_level(2), 100)
        
        # Test level 3 (282 XP)
        level_3_xp = self.profile.calculate_xp_for_level(3)
        self.assertTrue(280 <= level_3_xp <= 285)

    def test_level_update(self):
        # Give user enough XP for level 3
        self.profile.total_xp = 300
        self.profile.update_level()
        
        self.assertEqual(self.profile.current_level, 3)

    def test_xp_progress_properties(self):
        self.profile.total_xp = 150
        self.profile.current_level = 2
        
        # Should be at level 2 with 50 XP progress
        progress = self.profile.xp_progress_in_current_level
        self.assertEqual(progress, 50)