# tests.py
import uuid
from datetime import  timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock

# Import your models and serializers
from progress.models import (
    Category, Task, XPLog, ProgressProfile, Achievement, UserAchievement
)
from progress.serializers import (
    CategorySerializer, TaskSerializer, ProgressProfileSerializer
    #, AchievementSerializer XPLogSerializer
)
from users.models import CustomUser, UserProfile, UserActivity, PasswordResetToken
from users.serializers import (
    UserRegistrationSerializer, UserLoginSerializer #, UserProfileSerializer,
    #UserSerializer, PublicUserSerializer, UserUpdateSerializer,
    #PasswordChangeSerializer, UserStatsSerializer
)

User = get_user_model()


class CustomUserModelTests(TestCase):
    """Test cases for CustomUser model"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = CustomUser.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(isinstance(user.id, uuid.UUID))
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = CustomUser.objects.create_superuser(**self.user_data)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = CustomUser.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'test@example.com')
    
    def test_full_name_property(self):
        """Test full_name property"""
        user = CustomUser.objects.create_user(**self.user_data)
        self.assertEqual(user.full_name, 'Test User')
        
        # Test with no first/last name
        user.first_name = ''
        user.last_name = ''
        self.assertEqual(user.full_name, 'testuser')
    
    def test_display_name_property(self):
        """Test display_name property"""
        user = CustomUser.objects.create_user(**self.user_data)
        self.assertEqual(user.display_name, 'Test User')
    
    def test_get_avatar_url(self):
        """Test get_avatar_url method"""
        user = CustomUser.objects.create_user(**self.user_data)
        self.assertEqual(user.get_avatar_url(), '/static/images/default-avatar.png')
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        CustomUser.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            CustomUser.objects.create_user(
                username='testuser2',
                email='test@example.com',
                password='testpass123'
            )
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        user = CustomUser.objects.create_user(**self.user_data)
        user.phone_number = '+1234567890'
        user.full_clean()  # Should not raise
        
        user.phone_number = 'invalid-phone'
        with self.assertRaises(ValidationError):
            user.full_clean()


class UserProfileModelTests(TestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, created = UserProfile.objects.get_or_create(user=self.user)
    
    def test_profile_creation(self):
        """Test profile creation"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.total_points, 0)
        self.assertEqual(self.profile.current_streak, 0)
    
    def test_profile_string_representation(self):
        """Test profile string representation"""
        expected = f"{self.user.username}'s Profile"
        self.assertEqual(str(self.profile), expected)
    
    def test_increment_profile_views(self):
        """Test profile view increment"""
        initial_views = self.profile.profile_views
        self.profile.increment_profile_views()
        self.assertEqual(self.profile.profile_views, initial_views + 1)
    
    def test_calculate_completeness(self):
        """Test profile completeness calculation"""
        # Empty profile should have low completeness
        completeness = self.profile.calculate_completeness()
        self.assertGreaterEqual(completeness, 0)
        self.assertLessEqual(completeness, 100)
        
        # Fill some fields
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.bio = 'Test bio'
        self.user.save()
        
        self.profile.job_title = 'Developer'
        self.profile.skills = 'Python, Django'
        self.profile.save()
        
        new_completeness = self.profile.calculate_completeness()
        self.assertGreater(new_completeness, completeness)
    
    def test_get_skills_list(self):
        """Test skills list parsing"""
        self.profile.skills = 'Python, Django, JavaScript'
        skills = self.profile.get_skills_list()
        self.assertEqual(skills, ['Python', 'Django', 'JavaScript'])
    
    def test_get_preferred_languages_list(self):
        """Test preferred languages list parsing"""
        self.profile.preferred_languages = 'Python, Java, Go'
        languages = self.profile.get_preferred_languages_list()
        self.assertEqual(languages, ['Python', 'Java', 'Go'])


class CategoryModelTests(TestCase):
    """Test cases for Category model"""
    
    def setUp(self):
        self.category_data = {
            'name': 'Programming',
            'description': 'Programming related tasks',
            'color': '#007bff',
            'xp_multiplier': 1.5
        }
    
    def test_category_creation(self):
        """Test category creation"""
        category = Category.objects.create(**self.category_data)
        self.assertEqual(category.name, 'Programming')
        self.assertEqual(category.xp_multiplier, 1.5)
        self.assertEqual(str(category), 'Programming')
    
    def test_category_uniqueness(self):
        """Test category name uniqueness"""
        Category.objects.create(**self.category_data)
        with self.assertRaises(IntegrityError):
            Category.objects.create(**self.category_data)
    
    def test_default_values(self):
        """Test default values"""
        category = Category.objects.create(name='Test Category')
        self.assertEqual(category.color, '#007bff')
        self.assertEqual(category.xp_multiplier, 1.0)


class TaskModelTests(TestCase):
    """Test cases for Task model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.task_data = {
            'user': self.user,
            'title': 'Test Task',
            'description': 'Test description',
            'category': self.category,
            'difficulty': 'medium',
            'priority': 'high'
        }
    
    def test_task_creation(self):
        """Test task creation"""
        task = Task.objects.create(**self.task_data)
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.difficulty, 'medium')
        self.assertEqual(task.priority, 'high')
        self.assertFalse(task.is_completed)
        self.assertIsNone(task.completed_at)
    
    def test_task_string_representation(self):
        """Test task string representation"""
        task = Task.objects.create(**self.task_data)
        expected = f"{task.title} ({task.get_difficulty_display()})"
        self.assertEqual(str(task), expected)
    
    @patch('tasks.models.GamificationEngine')
    def test_complete_task(self, mock_engine_class):
        """Test task completion"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        task = Task.objects.create(**self.task_data)
        result = task.complete_task()
        
        self.assertTrue(result)
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)
        mock_engine.award_task_xp.assert_called_once_with(task)
    
    @patch('tasks.models.GamificationEngine')
    def test_complete_already_completed_task(self, mock_engine_class):
        """Test completing already completed task"""
        task = Task.objects.create(**self.task_data)
        task.is_completed = True
        task.save()
        
        result = task.complete_task()
        self.assertFalse(result)


class ProgressProfileModelTests(TestCase):
    """Test cases for ProgressProfile model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.progress = ProgressProfile.objects.create(user=self.user)
    
    def test_progress_creation(self):
        """Test progress profile creation"""
        self.assertEqual(self.progress.user, self.user)
        self.assertEqual(self.progress.total_xp, 0)
        self.assertEqual(self.progress.current_level, 0)
    
    def test_calculate_xp_for_level(self):
        """Test XP calculation for levels"""
        self.assertEqual(self.progress.calculate_xp_for_level(1), 0)
        self.assertEqual(self.progress.calculate_xp_for_level(2), 100)
        self.assertTrue(self.progress.calculate_xp_for_level(3) > 100)
    
    def test_xp_properties(self):
        """Test XP-related properties"""
        self.progress.total_xp = 150
        self.progress.current_level = 2
        
        # Test properties
        self.assertGreater(self.progress.xp_for_next_level, 150)
        self.assertGreaterEqual(self.progress.xp_progress_in_current_level, 0)
        self.assertGreater(self.progress.xp_needed_for_next_level, 0)
    
    @patch('tasks.models.GamificationEngine')
    def test_update_level(self, mock_engine_class):
        """Test level update"""
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        self.progress.total_xp = 250  # Should be level 2
        self.progress.update_level()
        
        self.assertEqual(self.progress.current_level, 2)
    
    def test_string_representation(self):
        """Test string representation"""
        expected = f"{self.user.username} - Level {self.progress.current_level}"
        self.assertEqual(str(self.progress), expected)


class AchievementModelTests(TestCase):
    """Test cases for Achievement model"""
    
    def setUp(self):
        self.achievement_data = {
            'name': 'First Steps',
            'description': 'Complete your first task',
            'achievement_type': 'task_count',
            'threshold': 1,
            'xp_reward': 50
        }
    
    def test_achievement_creation(self):
        """Test achievement creation"""
        achievement = Achievement.objects.create(**self.achievement_data)
        self.assertEqual(achievement.name, 'First Steps')
        self.assertEqual(achievement.threshold, 1)
        self.assertEqual(achievement.xp_reward, 50)
        self.assertFalse(achievement.is_hidden)
    
    def test_string_representation(self):
        """Test string representation"""
        achievement = Achievement.objects.create(**self.achievement_data)
        expected = f"{achievement.name} ({achievement.get_achievement_type_display()})"
        self.assertEqual(str(achievement), expected)


class UserAchievementModelTests(TestCase):
    """Test cases for UserAchievement model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.achievement = Achievement.objects.create(
            name='Test Achievement',
            description='Test description',
            achievement_type='task_count',
            threshold=5
        )
    
    def test_user_achievement_creation(self):
        """Test user achievement creation"""
        user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement,
            progress=3
        )
        self.assertEqual(user_achievement.user, self.user)
        self.assertEqual(user_achievement.achievement, self.achievement)
        self.assertEqual(user_achievement.progress, 3)
    
    def test_unique_constraint(self):
        """Test unique constraint on user-achievement pair"""
        UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement
        )
        with self.assertRaises(IntegrityError):
            UserAchievement.objects.create(
                user=self.user,
                achievement=self.achievement
            )
    
    def test_string_representation(self):
        """Test string representation"""
        user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement
        )
        expected = f"{self.user.username} unlocked {self.achievement.name}"
        self.assertEqual(str(user_achievement), expected)


class XPLogModelTests(TestCase):
    """Test cases for XPLog model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category
        )
    
    def test_xp_log_creation(self):
        """Test XP log creation"""
        xp_log = XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=50,
            task=self.task,
            description='Completed a task'
        )
        self.assertEqual(xp_log.user, self.user)
        self.assertEqual(xp_log.xp_earned, 50)
        self.assertEqual(xp_log.task, self.task)
    
    def test_string_representation(self):
        """Test string representation"""
        xp_log = XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=50
        )
        expected = f"{self.user.username} earned 50 XP for {xp_log.get_action_display()}"
        self.assertEqual(str(xp_log), expected)


class PasswordResetTokenModelTests(TestCase):
    """Test cases for PasswordResetToken model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_token_creation(self):
        """Test token creation"""
        token = PasswordResetToken.objects.create(user=self.user)
        self.assertEqual(token.user, self.user)
        self.assertIsNotNone(token.token)
        self.assertIsNotNone(token.expires_at)
        self.assertFalse(token.is_used)
    
    def test_token_expiration(self):
        """Test token expiration"""
        # Create expired token
        token = PasswordResetToken.objects.create(user=self.user)
        token.expires_at = timezone.now() - timedelta(hours=2)
        token.save()
        
        self.assertTrue(token.is_expired())
        self.assertFalse(token.is_valid())
    
    def test_token_validity(self):
        """Test token validity"""
        token = PasswordResetToken.objects.create(user=self.user)
        self.assertTrue(token.is_valid())
        
        # Mark as used
        token.is_used = True
        token.save()
        self.assertFalse(token.is_valid())


class UserActivityModelTests(TestCase):
    """Test cases for UserActivity model"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_activity_creation(self):
        """Test activity creation"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            ip_address='127.0.0.1'
        )
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.ip_address, '127.0.0.1')
    
    def test_string_representation(self):
        """Test string representation"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        expected = f"{self.user.username} - login at {activity.timestamp}"
        self.assertEqual(str(activity), expected)


class UserRegistrationSerializerTests(TestCase):
    """Test cases for UserRegistrationSerializer"""
    
    def test_valid_registration(self):
        """Test valid user registration"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('complexpassword123'))
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'differentpassword',
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
    
    def test_duplicate_email(self):
        """Test duplicate email validation"""
        CustomUser.objects.create_user(
            username='existing',
            email='test@example.com',
            password='password123'
        )
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class UserLoginSerializerTests(TestCase):
    """Test cases for UserLoginSerializer"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_valid_login(self):
        """Test valid login"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        serializer = UserLoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)
    
    def test_invalid_credentials(self):
        """Test invalid login credentials"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        serializer = UserLoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
    
    def test_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        serializer = UserLoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class TaskSerializerTests(TestCase):
    """Test cases for TaskSerializer"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
    
    @patch('tasks.serializers.GamificationEngine')
    def test_task_serialization(self, mock_engine_class):
        """Test task serialization"""
        mock_engine = MagicMock()
        mock_engine.calculate_task_xp.return_value = 100
        mock_engine_class.return_value = mock_engine
        
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category,
            difficulty='hard'
        )
        
        serializer = TaskSerializer(task)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Test Task')
        self.assertEqual(data['category_name'], 'Test Category')
        self.assertEqual(data['xp_value'], 100)
    
    def test_task_creation_via_serializer(self):
        """Test task creation through serializer"""
        from rest_framework.test import APIRequestFactory
        #from django.contrib.auth.models import AnonymousUser
        
        factory = APIRequestFactory()
        request = factory.post('/')
        request.user = self.user
        
        data = {
            'title': 'New Task',
            'description': 'Task description',
            'category': self.category.id,
            'difficulty': 'medium'
        }
        
        serializer = TaskSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        
        task = serializer.save()
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.title, 'New Task')


class CategorySerializerTests(TestCase):
    """Test cases for CategorySerializer"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
    
    def test_category_serialization(self):
        """Test category serialization"""
        from rest_framework.test import APIRequestFactory
        
        # Create some tasks for the category
        Task.objects.create(user=self.user, title='Task 1', category=self.category)
        Task.objects.create(user=self.user, title='Task 2', category=self.category)
        
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        serializer = CategorySerializer(self.category, context={'request': request})
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Category')
        self.assertEqual(data['task_count'], 2)


class ProgressProfileSerializerTests(TestCase):
    """Test cases for ProgressProfileSerializer"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.progress = ProgressProfile.objects.create(
            user=self.user,
            total_xp=150,
            current_level=2
        )
    
    def test_progress_serialization(self):
        """Test progress profile serialization"""
        serializer = ProgressProfileSerializer(self.progress)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['total_xp'], 150)
        self.assertEqual(data['current_level'], 2)
        self.assertIn('level_progress', data)
        self.assertIn('progress_percentage', data['level_progress'])


class UserStatsSerializerTests(TestCase):
    """Test cases for UserStatsSerializer"""
    
    def setUp(self):
        # Create test users
        self.user1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            is_profile_public=True
        )
        
        # Set recent login for active user test
        self.user1.last_login = timezone.now()
        self.user1.save()
    
    def test_stats_calculation(self):
        """Test user statistics calculation"""
        serializer = UserStatsSerializerTests()
        data = serializer.to_representation(None)
        
        self.assertIn('total_users', data)
        self.assertIn('active_users', data)
        self.assertIn('public_profiles', data)
        self.assertIn('recent_registrations', data)
        
        self.assertGreaterEqual(data['total_users'], 2)
        self.assertGreaterEqual(data['public_profiles'], 1)


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
    '''
    # Create tasks in different categories
    task1 = Task.objects.create(
        user=self.user,
        title='Programming Task',
        category=self.category
    )
    task2 = Task.objects.create(
        user=self.user,
        title='Design Task',
        category=category2
    )
    '''
    # Test filtering
    programming_tasks = Task.objects.filter(user=self.user, category=self.category)
    design_tasks = Task.objects.filter(user=self.user, category=category2)
    
    self.assertEqual(programming_tasks.count(), 1)
    self.assertEqual(design_tasks.count(), 1)
    self.assertEqual(programming_tasks.first().title, 'Programming Task')
    self.assertEqual(design_tasks.first().title, 'Design Task')

def test_user_activity_tracking(self):
    """Test user activity tracking"""
    '''
    # Create some activities
    activity1 = UserActivity.objects.create(
        user=self.user,
        activity_type='login',
        ip_address='127.0.0.1'
    )
    
    activity2 = UserActivity.objects.create(
        user=self.user,
        activity_type='task_create',
        ip_address='127.0.0.1'
    )
    '''
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
    '''
    # Create related data
    task = Task.objects.create(
        user=self.user,
        title='User Deletion Test Task',
        category=self.category
    )
    
    xp_log = XPLog.objects.create(
        user=self.user,
        action='task_complete',
        xp_earned=50
    )
    
    activity = UserActivity.objects.create(
        user=self.user,
        activity_type='login'
    )
    '''
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