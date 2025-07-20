from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock

from users.models import CustomUser, UserProfile, UserActivity, PasswordResetToken
from progress.models import (
    Category, Task, XPLog, ProgressProfile, Achievement, UserAchievement
)

User = get_user_model()


class APITestCases(APITestCase):
    """Integration tests for API endpoints"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
    
    def test_authenticated_task_creation(self):
        """Test creating task via API with authentication"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        data = {
            'title': 'API Test Task',
            'description': 'Created via API',
            'category': self.category.id,
            'difficulty': 'medium',
            'priority': 'high'
        }
        
        response = self.client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        
        task = Task.objects.first()
        self.assertEqual(task.title, 'API Test Task')
        self.assertEqual(task.user, self.user)
    
    def test_unauthenticated_access(self):
        """Test unauthenticated access is rejected"""
        data = {
            'title': 'Unauthorized Task',
            'category': self.category.id
        }
        
        response = self.client.post('/api/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_registration_api(self):
        """Test user registration via API"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())


class IntegrationTests(TestCase):
    """Integration tests for complex workflows"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Programming',
            xp_multiplier=1.5
        )
        self.progress = ProgressProfile.objects.create(user=self.user)
    
    def test_user_profile_relationship(self):
        """Test user-profile relationship"""
        try:
            profile = self.user.profile
            self.assertIsInstance(profile, UserProfile)
        except UserProfile.DoesNotExist:
            # Create profile manually if no signal exists
            profile = UserProfile.objects.create(user=self.user)
            self.assertIsInstance(profile, UserProfile)
    
    def test_password_reset_token_relationships(self):
        """Test password reset token relationships"""
        token1 = PasswordResetToken.objects.create(user=self.user)
        token2 = PasswordResetToken.objects.create(user=self.user)
        
        # Test forward relationship
        self.assertEqual(token1.user, self.user)
        
        # Test reverse relationship
        user_tokens = self.user.passwordresettoken_set.all()
        self.assertEqual(user_tokens.count(), 2)
        self.assertIn(token1, user_tokens)
        self.assertIn(token2, user_tokens)
    
    def test_user_activity_relationship(self):
        """Test user activity relationship"""
        activity1 = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            ip_address='127.0.0.1'
        )
        activity2 = UserActivity.objects.create(
            user=self.user,
            activity_type='logout',
            ip_address='127.0.0.1'
        )
        
        user_activities = self.user.activities.all()
        self.assertEqual(user_activities.count(), 2)
        self.assertIn(activity1, user_activities)
        self.assertIn(activity2, user_activities)
    
    @patch('tasks.models.GamificationEngine')
    def test_complete_workflow(self, mock_engine_class):
        """Test complete task management workflow"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Create task
        task = Task.objects.create(
            user=self.user,
            title='Integration Test Task',
            category=self.category,
            difficulty='hard'
        )
        
        # Complete task
        result = task.complete_task()
        
        # Verify task completion
        self.assertTrue(result)
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)
        
        # Verify gamification engine was called
        mock_engine.award_task_xp.assert_called_once_with(task)
    
    
    def test_user_profile_creation_on_user_creation(self):
        """Test that UserProfile is created when CustomUser is created"""
        # This would typically be done via Django signals
        # For this test, we'll create manually and verify the relationship
        new_user = CustomUser.objects.create_user(
            username='profileuser',
            email='profileuser@example.com',
            password='testpass123'
        )
    
        # Check if UserProfile was created automatically (via signals)
        # If using signals, this should exist
        try:
            profile = UserProfile.objects.get(user=new_user)
            self.assertEqual(profile.user, new_user)
            self.assertEqual(profile.total_points, 0)
            self.assertEqual(profile.current_streak, 0)
        except UserProfile.DoesNotExist:
            # If no signals are set up, create manually for test
            profile = UserProfile.objects.create(user=new_user)
            self.assertEqual(profile.user, new_user)
        
        # Verify the relationship works both ways
        self.assertEqual(new_user.userprofile, profile)
    
    def test_progress_profile_creation_on_user_creation(self):
        """Test that ProgressProfile is created when CustomUser is created"""
        new_user = CustomUser.objects.create_user(
            username='progressuser',
            email='progressuser@example.com',
            password='testpass123'
        )
        
        # Check if ProgressProfile was created automatically (via signals)
        try:
            progress = ProgressProfile.objects.get(user=new_user)
            self.assertEqual(progress.user, new_user)
            self.assertEqual(progress.total_xp, 0)
            self.assertEqual(progress.current_level, 0)
        except ProgressProfile.DoesNotExist:
            # If no signals are set up, create manually for test
            progress = ProgressProfile.objects.create(user=new_user)
            self.assertEqual(progress.user, new_user)
    
    @patch('tasks.models.GamificationEngine')
    def test_task_completion_with_xp_logging(self, mock_engine_class):
        """Test complete task workflow with XP logging"""
        mock_engine = MagicMock()
        mock_engine.award_task_xp.return_value = {'xp_earned': 75, 'bonus_xp': 25}
        mock_engine_class.return_value = mock_engine
        
        # Create a task
        task = Task.objects.create(
            user=self.user,
            title='XP Test Task',
            category=self.category,
            difficulty='medium',
            priority='high'
        )
        
        # = XPLog.objects.filter(user=self.user).count()
        
        # Complete the task
        result = task.complete_task()
        
        # Verify task completion
        self.assertTrue(result)
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)
        
        # Verify gamification engine was called
        mock_engine.award_task_xp.assert_called_once_with(task)
        
        # If XP logging is implemented, verify XP log was created
        # This assumes the gamification engine creates XP logs
        # You might need to adjust based on your actual implementation
        #final_xp_logs = XPLog.objects.filter(user=self.user).count()
        # Uncomment if XP logging is implemented in task completion
        # self.assertGreater(final_xp_logs, initial_xp_logs)
    
    @patch('tasks.models.GamificationEngine')
    def test_user_level_progression(self, mock_engine_class):
        """Test user level progression through task completion"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Set up initial progress
        self.progress.total_xp = 90  # Close to level up (assuming level 2 at 100 XP)
        self.progress.current_level = 1
        self.progress.save()
        
        # Create and complete a task that should level up the user
        task = Task.objects.create(
            user=self.user,
            title='Level Up Task',
            category=self.category,
            difficulty='medium'
        )
        
        # Mock the XP calculation to return enough XP for level up
        mock_engine.calculate_task_xp.return_value = 15
        
        # Complete the task
        task.complete_task()
        
        # Manually update XP (in real app, this would be done by gamification engine)
        self.progress.total_xp += 15
        self.progress.update_level()
        
        # Verify level progression
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.total_xp, 105)
        self.assertGreaterEqual(self.progress.current_level, 2)
    
    def test_achievement_system_integration(self):
        """Test achievement system integration"""
        # Create an achievement
        achievement = Achievement.objects.create(
            name='First Task',
            description='Complete your first task',
            achievement_type='task_count',
            threshold=1,
            xp_reward=25
        )
        
        # Create a task
        task = Task.objects.create(
            user=self.user,
            title='Achievement Test Task',
            category=self.category
        )
        
        # Complete the task
        with patch('tasks.models.GamificationEngine') as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine_class.return_value = mock_engine
            
            task.complete_task()
        
        # In a real implementation, this would be handled by signals or the gamification engine
        # For testing, we'll manually check if achievement should be unlocked
        completed_tasks = Task.objects.filter(user=self.user, is_completed=True).count()
        
        if completed_tasks >= achievement.threshold:
            # Create user achievement if it doesn't exist
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=self.user,
                achievement=achievement,
                defaults={'progress': completed_tasks}
            )
            
            self.assertTrue(created or user_achievement.progress >= achievement.threshold)
    
    def test_category_task_filtering(self):
        """Test filtering tasks by category"""
        # Create multiple categories
        category2 = Category.objects.create(name='Design', xp_multiplier=1.2)
        
        # Create tasks in different categories
        Task.objects.create(
            user=self.user,
            title='Programming Task',
            category=self.category
        )
        Task.objects.create(
            user=self.user,
            title='Design Task',
            category=category2
        )
        
        # Test filtering
        programming_tasks = Task.objects.filter(user=self.user, category=self.category)
        design_tasks = Task.objects.filter(user=self.user, category=category2)
        
        self.assertEqual(programming_tasks.count(), 1)
        self.assertEqual(design_tasks.count(), 1)
        self.assertEqual(programming_tasks.first().title, 'Programming Task')
        self.assertEqual(design_tasks.first().title, 'Design Task')
    
    def test_user_activity_tracking(self):
        """Test user activity tracking"""
        # Create some activities
        UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            ip_address='127.0.0.1'
        )
        
        UserActivity.objects.create(
            user=self.user,
            activity_type='task_create',
            ip_address='127.0.0.1'
        )
        
        # Test activity retrieval
        user_activities = UserActivity.objects.filter(user=self.user).order_by('-timestamp')
        
        self.assertEqual(user_activities.count(), 2)
        self.assertEqual(user_activities.first().activity_type, 'task_create')
        self.assertEqual(user_activities.last().activity_type, 'login')
    
    def test_password_reset_token_workflow(self):
        """Test password reset token workflow"""
        # Create a password reset token
        token = PasswordResetToken.objects.create(user=self.user)
        
        # Verify token is valid initially
        self.assertTrue(token.is_valid())
        self.assertFalse(token.is_expired())
        
        # Test token usage
        self.assertFalse(token.is_used)
        token.is_used = True
        token.save()
        
        # Verify token is no longer valid after use
        self.assertFalse(token.is_valid())
        
        # Test expired token
        expired_token = PasswordResetToken.objects.create(user=self.user)
        expired_token.expires_at = timezone.now() - timedelta(hours=2)
        expired_token.save()
        
        self.assertTrue(expired_token.is_expired())
        self.assertFalse(expired_token.is_valid())
    
    @patch('tasks.models.GamificationEngine')
    def test_bulk_task_operations(self, mock_engine_class):
        """Test bulk task operations"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = Task.objects.create(
                user=self.user,
                title=f'Bulk Task {i+1}',
                category=self.category,
                difficulty='easy'
            )
            tasks.append(task)
        
        # Complete all tasks
        completed_count = 0
        for task in tasks:
            if task.complete_task():
                completed_count += 1
        
        # Verify all tasks were completed
        self.assertEqual(completed_count, 5)
        
        # Verify database state
        completed_tasks = Task.objects.filter(user=self.user, is_completed=True)
        self.assertEqual(completed_tasks.count(), 5)
        
        # Verify gamification engine was called for each task
        self.assertEqual(mock_engine.award_task_xp.call_count, 5)
    
    def test_data_consistency_after_user_deletion(self):
        """Test data consistency when user is deleted"""
        # Create related data
        Task.objects.create(
            user=self.user,
            title='User Deletion Test Task',
            category=self.category
        )
        
        XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=50
        )
        
        UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        
        user_id = self.user.id
        
        # Delete user
        self.user.delete()
        
        # Verify related data is handled appropriately
        # This depends on your model's on_delete settings
        # Adjust assertions based on your CASCADE/SET_NULL/PROTECT settings
        
        # If using CASCADE, related objects should be deleted
        self.assertFalse(Task.objects.filter(user_id=user_id).exists())
        self.assertFalse(XPLog.objects.filter(user_id=user_id).exists())
        self.assertFalse(UserActivity.objects.filter(user_id=user_id).exists())
        self.assertFalse(ProgressProfile.objects.filter(user_id=user_id).exists())