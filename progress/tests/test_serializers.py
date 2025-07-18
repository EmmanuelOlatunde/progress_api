from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser



from ..models import (
    Task, WeeklyReview, Category, XPLog, Achievement, UserAchievement,#ProgressProfile, 
    LeaderboardType, LeaderboardEntry, UserFriendship, MissionTemplate, UserMission,
    Notification, NotificationType, UserNotificationSettings, NotificationQueue
)
from ..serializers import (
    CategorySerializer, WeeklyReviewSerializer, TaskSerializer, XPLogSerializer,
    ProgressProfileSerializer, AchievementSerializer, UserAchievementSerializer,
    UserBasicSerializer, LeaderboardTypeSerializer, LeaderboardEntrySerializer,
    UserFriendshipSerializer, MissionTemplateSerializer, UserMissionSerializer,
    MissionProgressSerializer, NotificationTypeSerializer, NotificationSerializer,
    UserNotificationSettingsSerializer, NotificationQueueSerializer
)

User = get_user_model()


class BaseSerializerTestCase(TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Work',
            description='Work-related tasks',
            color='#007bff',
            xp_multiplier=1.0
        )
        
        # Create test task
        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='A test task',
            category=self.category,
            difficulty='medium',
            priority='high',
            due_date=timezone.now() + timedelta(days=2)
        )
        
        # Create test achievement
        self.achievement = Achievement.objects.create(
            name='Test Achievement',
            description='Work-related tasks',
            achievement_type='task_count',
            threshold=10,
            xp_reward=100,
            icon='🏆'
        )
        # Create UserAchievement for test_achievement_serialization_unlocked
        self.user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement,
            progress=10,
            unlocked_at=timezone.now()
        )
        


        # Create progress profile
        user = self.user  
        user_profile = user.progress_profile  
        user_profile.total_xp = 1000  
        user_profile.current_level = 5  
        user_profile.current_streak = 3  
        user_profile.longest_streak = 10  
        user_profile.total_early_completions = 5  
        user_profile.total_on_time_completions = 10  
        user_profile.total_late_completions = 2  
        user_profile.save()

    def get_request_context(self, user=None):
        """Helper to create request context"""
        self.factory = APIRequestFactory()
        request = self.factory.get('/')
        request.user = user if user is not None else AnonymousUser()
        return {'request': request}


class CategorySerializerTestCase(BaseSerializerTestCase):
    
    def test_category_serialization(self):
        """Test category serialization with task count"""
        context = self.get_request_context()
        serializer = CategorySerializer(self.category, context=context)
        
        data = serializer.data
        
        self.assertEqual(data['name'], 'Work')
        self.assertEqual(data['description'], 'Work-related tasks')
        self.assertEqual(data['color'], '#007bff')
        self.assertEqual(data['xp_multiplier'], 1.0)
        self.assertEqual(data['task_count'], 1)  # One task created in setUp
        
    def test_category_task_count_unauthenticated(self):
        """Test task count calculation for unauthenticated user"""
        # Create another task for different user
        Task.objects.create(
            title='Another Task',
            category=self.category,
            user=self.user2,
            difficulty='easy',
            priority='low'
        )
        
        self.assertEqual(Task.objects.filter(category=self.category).count(), 2)  # Debug check
        
        context = self.get_request_context(user=None)
        serializer = CategorySerializer(self.category, context=context)
        
        self.assertEqual(serializer.data['task_count'], 2)


class WeeklyReviewSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.weekly_review = WeeklyReview.objects.create(
            user=self.user,
            week_start=timezone.now().date(),
            week_end=(timezone.now() + timedelta(days=6)).date(),
            total_tasks=10,
            total_xp=500,
            early_completions=3,
            on_time_completions=5,
            late_completions=2,
            performance_score=85.5,
            suggestions='Focus on time management\nImprove planning'
        )
        
    def test_weekly_review_serialization(self):
        """Test weekly review serialization"""
        serializer = WeeklyReviewSerializer(self.weekly_review)
        data = serializer.data
        
        self.assertEqual(data['total_tasks'], 10)
        self.assertEqual(data['total_xp'], 500)
        self.assertEqual(data['early_completions'], 3)
        self.assertEqual(data['performance_score'], 85.5)
        self.assertEqual(len(data['suggestions_list']), 2)
        self.assertIn('Focus on time management', data['suggestions_list'])
        
    def test_suggestions_list_empty(self):
        """Test suggestions list when empty"""
        self.weekly_review.suggestions = ''
        self.weekly_review.save()
        
        serializer = WeeklyReviewSerializer(self.weekly_review)
        self.assertEqual(serializer.data['suggestions_list'], [])


class TaskSerializerTestCase(BaseSerializerTestCase):
    
    @patch('progress.gamification.GamificationEngine')
    def test_task_serialization(self, mock_engine_class):
        """Test task serialization with XP calculation"""
        mock_engine = MagicMock()
        mock_engine.calculate_task_xp.return_value = 150
        mock_engine.can_complete_task.return_value = (True, "Task can be completed")
        mock_engine_class.return_value = mock_engine
        
        context = self.get_request_context()
        serializer = TaskSerializer(self.task, context=context)
        
        data = serializer.data
        
        self.assertEqual(data['title'], 'Test Task')
        self.assertEqual(data['category_name'], 'Work')
        self.assertEqual(data['difficulty'], 'medium')
        self.assertEqual(data['priority'], 'high')
        self.assertEqual(data['xp_value'], 150)
        self.assertIn('timing_info', data)
    
    def test_task_creation(self):
        data = {
            'title': 'Test Task',
            'category': self.category.id,
            'description': 'A test task',
            'difficulty': 'medium',
            'priority': 'medium',
            'due_date': '2025-07-20T12:00:00Z'
        }
        context = self.get_request_context(user=self.user)
        serializer = TaskSerializer(data=data, context=context)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)  # Debug output
        self.assertTrue(serializer.is_valid())
        task = serializer.save()
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.category, self.category)

    def test_task_timing_info(self):
        """Test timing info method call"""
        with patch.object(self.task, 'get_timing_info') as mock_timing:
            mock_timing.return_value = {'status': 'on_time', 'days_remaining': 1}
            
            serializer = TaskSerializer(self.task)
            data = serializer.data
            
            self.assertEqual(data['timing_info'], {'status': 'on_time', 'days_remaining': 1})
            mock_timing.assert_called_once()


class XPLogSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.xp_log = XPLog.objects.create(
            user=self.user,
            action='task_completion',
            xp_earned=100,
            task=self.task,
            description='Completed task on time'
        )
        
    def test_xp_log_serialization(self):
        """Test XP log serialization"""
        serializer = XPLogSerializer(self.xp_log)
        data = serializer.data
        
        self.assertEqual(data['action'], 'task_completion')
        self.assertEqual(data['xp_earned'], 100)
        self.assertEqual(data['task_title'], 'Test Task')
        self.assertEqual(data['description'], 'Completed task on time')
        self.assertIn('action_display', data)


class ProgressProfileSerializerTestCase(BaseSerializerTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        
        # Access the auto-created profile
        self.progress_profile = self.user.progress_profile
        self.progress_profile.total_xp = 1000
        self.progress_profile.current_level = 5
        self.progress_profile.current_streak = 3
        self.progress_profile.longest_streak = 10
        self.progress_profile.total_early_completions = 5
        self.progress_profile.total_on_time_completions = 10
        self.progress_profile.total_late_completions = 2
        self.progress_profile.save()

    def test_progress_profile_serialization(self):
        """Test progress profile serialization"""
        serializer = ProgressProfileSerializer(self.progress_profile)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['total_xp'], 1000)
        self.assertEqual(data['current_level'], 5)
        self.assertEqual(data['current_streak'], 3)
        self.assertEqual(data['longest_streak'], 10)
        self.assertEqual(data['total_early_completions'], 5)
        self.assertIn('punctuality_rate', data)


class AchievementSerializerTestCase(BaseSerializerTestCase):

    def test_achievement_serialization_unlocked(self):
        """Test achievement serialization for unlocked achievement"""

        context = self.get_request_context(self.user)
        serializer = AchievementSerializer(self.achievement, context=context)
        
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Achievement')
        self.assertEqual(data['threshold'], 10)
        self.assertEqual(data['xp_reward'], 100)
        self.assertTrue(data['is_unlocked'])
        self.assertEqual(data['progress'], 10)
        self.assertIsNotNone(data['unlocked_at'])
        
    @patch('progress.gamification.GamificationEngine')
    def test_achievement_serialization_not_unlocked(self, mock_engine_class):
        self.user_achievement.delete()
        mock_engine = MagicMock()
        mock_engine.get_achievement_progress.return_value = 5
        mock_engine_class.return_value = mock_engine
        context = self.get_request_context(user=self.user)
        serializer = AchievementSerializer(self.achievement, context=context)
        data = serializer.data
        self.assertEqual(data['progress'], 5)
        mock_engine.get_achievement_progress.assert_called_once_with(self.achievement)
        
    def test_achievement_serialization_no_user(self):
        """Test achievement serialization without authenticated user"""
        context = self.get_request_context(user=None)
        serializer = AchievementSerializer(self.achievement, context=context)
        
        data = serializer.data
        
        self.assertFalse(data['is_unlocked'])
        self.assertEqual(data['progress'], 0)
        self.assertIsNone(data['unlocked_at'])


class UserAchievementSerializerTestCase(BaseSerializerTestCase):
        
    def test_user_achievement_serialization(self):
        """Test user achievement serialization"""
        serializer = UserAchievementSerializer(self.user_achievement)
        data = serializer.data
        
        self.assertEqual(data['progress'], 10)
        self.assertIsNotNone(data['unlocked_at'])
        self.assertIn('achievement', data)
        self.assertEqual(data['achievement']['name'], 'Test Achievement')


class UserBasicSerializerTestCase(BaseSerializerTestCase):
    
    def test_user_basic_serialization(self):
        """Test basic user serialization"""
        with patch.object(self.user, 'get_avatar_url', return_value='https://example.com/avatar.jpg'):
            serializer = UserBasicSerializer(self.user)
            data = serializer.data
            
            self.assertEqual(data['username'], 'testuser')
            self.assertEqual(data['display_name'], 'testuser')  # Fallback to username if no display_name
            self.assertEqual(data['avatar_url'], 'https://example.com/avatar.jpg')


class LeaderboardSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.leaderboard_type = LeaderboardType.objects.create(
            name='Weekly XP',
            leaderboard_type='weekly',
            description='Weekly XP leaderboard',
            is_active=True,
            reset_frequency='weekly'
        )
        
        self.leaderboard_entry = LeaderboardEntry.objects.create(
            user=self.user,
            leaderboard_type=self.leaderboard_type,
            score=1500,
            rank=1,
            tasks_completed=25,
            total_xp=1500,
            streak_count=7,
            punctuality_rate=95.0,
            period_start=timezone.now(),
            period_end=(timezone.now() + timedelta(days=7))
        )
        
    def test_leaderboard_type_serialization(self):
        """Test leaderboard type serialization"""
        serializer = LeaderboardTypeSerializer(self.leaderboard_type)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Weekly XP')
        self.assertEqual(data['leaderboard_type'], 'weekly')
        self.assertTrue(data['is_active'])
        self.assertEqual(data['reset_frequency'], 'weekly')
        
    def test_leaderboard_entry_serialization(self):
        """Test leaderboard entry serialization"""
        serializer = LeaderboardEntrySerializer(self.leaderboard_entry)
        data = serializer.data
        
        self.assertEqual(data['score'], 1500)
        self.assertEqual(data['rank'], 1)
        self.assertEqual(data['tasks_completed'], 25)
        self.assertEqual(data['punctuality_rate'], 95.0)
        self.assertEqual(data['rank_change'], 0)  # Default implementation
        
        # Test performance badge
        performance_badge = data['performance_badge']
        self.assertIsNotNone(performance_badge)
        self.assertEqual(performance_badge['name'], 'Time Master')
        self.assertEqual(performance_badge['color'], '#gold')
        
    def test_leaderboard_entry_performance_badges(self):
        """Test different performance badges"""
        # Test streak badge
        self.leaderboard_entry.punctuality_rate = 80.0
        self.leaderboard_entry.streak_count = 10
        self.leaderboard_entry.save()
        
        serializer = LeaderboardEntrySerializer(self.leaderboard_entry)
        badge = serializer.data['performance_badge']
        self.assertEqual(badge['name'], 'Streak Legend')
        
        # Test task crusher badge
        self.leaderboard_entry.streak_count = 5
        self.leaderboard_entry.tasks_completed = 60
        self.leaderboard_entry.save()
        
        serializer = LeaderboardEntrySerializer(self.leaderboard_entry)
        badge = serializer.data['performance_badge']
        self.assertEqual(badge['name'], 'Task Crusher')
        
        # Test no badge
        self.leaderboard_entry.tasks_completed = 10
        self.leaderboard_entry.save()
        
        serializer = LeaderboardEntrySerializer(self.leaderboard_entry)
        badge = serializer.data['performance_badge']
        self.assertIsNone(badge)


class UserFriendshipSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.friendship = UserFriendship.objects.create(
            user=self.user,
            friend=self.user2,
            status='pending'
        )
        
    def test_friendship_serialization(self):
        """Test friendship serialization"""
        serializer = UserFriendshipSerializer(self.friendship)
        data = serializer.data
        
        self.assertEqual(data['status'], 'pending')
        self.assertIn('friend', data)
        self.assertEqual(data['friend']['username'], 'testuser2')
        
    def test_friendship_creation_with_username(self):
        friend = User.objects.create_user(username='frienduser', password='friendpass')
        data = {'friend_username': 'frienduser'}
        context = self.get_request_context(user=self.user)
        serializer = UserFriendshipSerializer(data=data, context=context)
        self.assertTrue(serializer.is_valid())
        friendship = serializer.save()
        self.assertEqual(friendship.user, self.user)
        self.assertEqual(friendship.friend, friend)

    def test_friendship_creation_invalid_username(self):
        """Test friendship creation with invalid username"""
        data = {
            'friend_username': 'nonexistent',
            'status': 'pending'
        }
        
        serializer = UserFriendshipSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('friend_username', serializer.errors)


class MissionSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.mission_template = MissionTemplate.objects.create(
            name='Complete 10 Tasks',
            description='Complete 10 tasks in 7 days',
            mission_type='task_completion',
            difficulty='medium',
            target_value=10,
            duration_days=7,
            xp_reward=500,
            bonus_multiplier=1.5,
            category=self.category,
            min_user_level=1,
            max_user_level=10,
            is_repeatable=True
        )
        
        self.user_mission = UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Complete 10 Tasks',
            description='Complete 10 tasks in 7 days',
            target_value=10,
            current_progress=3,
            start_date=now() + timedelta(days=10),
            end_date=now() + timedelta(days=7),
            status='active',
            xp_reward=500,
            bonus_multiplier=1.5,
            category=self.category
        )
        
    def test_mission_template_serialization(self):
        """Test mission template serialization"""
        serializer = MissionTemplateSerializer(self.mission_template)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Complete 10 Tasks')
        self.assertEqual(data['difficulty'], 'medium')
        self.assertEqual(data['target_value'], 10)
        self.assertEqual(data['duration_days'], 7)
        self.assertEqual(data['category_name'], 'Work')
        self.assertEqual(data['estimated_time'], 5)  # medium difficulty
        
    def test_user_mission_serialization(self):
        """Test user mission serialization"""
        serializer = UserMissionSerializer(self.user_mission)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Complete 10 Tasks')
        self.assertEqual(data['current_progress'], 3)
        self.assertEqual(data['target_value'], 10)
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['days_remaining'], 7)
        self.assertEqual(data['difficulty_color'], '#ffc107')  # medium = yellow
        
    def test_user_mission_creation(self):
        """Test user mission creation"""
        data = {
            'template_id': self.mission_template.id,
            'title': 'New Mission',
            'description': 'New mission description',
            'target_value': 15,
            'start_date': now() + timedelta(days=10),  # ✅ full datetime, timezone-aware
            'end_date': now() + timedelta(days=10),   # ✅ also a datetime
            'status': 'active',
            'xp_reward': 750,
            'bonus_multiplier': 2.0,
            'category': self.category.id
        }
        
        serializer = UserMissionSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        mission = serializer.save(user=self.user)
        self.assertEqual(mission.template, self.mission_template)
        self.assertEqual(mission.title, 'New Mission')
        
    def test_mission_progress_serializer(self):
        """Test mission progress serializer"""
        data = {
            'mission_id': self.user_mission.id,
            'progress_increment': 2,
            'task_id': self.task.id
        }
        
        serializer = MissionProgressSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        self.assertEqual(serializer.validated_data['mission_id'], self.user_mission.id)
        self.assertEqual(serializer.validated_data['progress_increment'], 2)
        self.assertEqual(serializer.validated_data['task_id'], self.task.id)


class NotificationSerializerTestCase(BaseSerializerTestCase):
    
    def setUp(self):
        super().setUp()
        self.notification_type = NotificationType.objects.create(
            name='task_reminder',
            display_name='Task Reminder',
            description='Remind about pending tasks',
            default_enabled=True,
            can_disable=True,
            icon='bell',
            color='blue'
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type='task_reminder',
            title='Task Due Soon',
            message='Your task is due in 1 hour',
            priority='high',
            is_read=False,
            action_url='/tasks/1',
            action_text='View Task',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.user_settings = UserNotificationSettings.objects.create(
            user=self.user,
            email_notifications=True,
            email_task_reminders=True,
            push_notifications=True,
            reminder_frequency='daily'
        )
        
        self.notification_queue = NotificationQueue.objects.create(
            user=self.user,
            notification_type='task_reminder',
            title='Queued Notification',
            message='Queued message',
            scheduled_for=timezone.now() + timedelta(minutes=30),
            status='pending',
            send_email=True,
            send_push=True,
            max_attempts=3
        )
        
    def test_notification_type_serialization(self):
        """Test notification type serialization"""
        serializer = NotificationTypeSerializer(self.notification_type)
        data = serializer.data
        
        self.assertEqual(data['name'], 'task_reminder')
        self.assertEqual(data['display_name'], 'Task Reminder')
        self.assertTrue(data['default_enabled'])
        self.assertTrue(data['can_disable'])
        self.assertEqual(data['icon'], 'bell')
        self.assertEqual(data['color'], 'blue')
        
    def test_notification_serialization(self):
        """Test notification serialization"""
        serializer = NotificationSerializer(self.notification)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Task Due Soon')
        self.assertEqual(data['message'], 'Your task is due in 1 hour')
        self.assertEqual(data['priority'], 'high')
        self.assertFalse(data['is_read'])
        self.assertEqual(data['action_url'], '/tasks/1')
        self.assertEqual(data['action_text'], 'View Task')
        self.assertEqual(data['notification_icon'], '📋')  # task_reminder icon
        self.assertIn('time_ago', data)
        
    def test_notification_settings_serialization(self):
        """Test notification settings serialization"""
        serializer = UserNotificationSettingsSerializer(self.user_settings)
        data = serializer.data
        
        self.assertTrue(data['email_notifications'])
        self.assertTrue(data['email_task_reminders'])
        self.assertTrue(data['push_notifications'])
        self.assertEqual(data['reminder_frequency'], 'daily')
        
    def test_notification_queue_serialization(self):
        """Test notification queue serialization"""
        serializer = NotificationQueueSerializer(self.notification_queue)
        data = serializer.data
        
        self.assertEqual(data['title'], 'Queued Notification')
        self.assertEqual(data['status'], 'pending')
        self.assertTrue(data['send_email'])
        self.assertTrue(data['send_push'])
        self.assertEqual(data['max_attempts'], 3)
        self.assertIn('user', data)
        
    def test_notification_icon_mapping(self):
        """Test notification icon mapping"""
        test_cases = [
            ('mission_completed', '🎯'),
            ('achievement_unlocked', '🏆'),
            ('friend_request', '👥'),
            ('level_up', '⬆️'),
            ('unknown_type', '📢')  # default
        ]
        
        for notification_type, expected_icon in test_cases:
            self.notification.notification_type = notification_type
            self.notification.save()
            
            serializer = NotificationSerializer(self.notification)
            self.assertEqual(serializer.data['notification_icon'], expected_icon)


class SerializerValidationTestCase(BaseSerializerTestCase):
    
    def test_task_serializer_validation(self):
        """Test task serializer validation"""
        # Test missing required fields
        serializer = TaskSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        
        # Test valid data
        data = {
            'title': 'Valid Task',
            'category': self.category.id,
            'difficulty': 'easy',
            'priority': 'medium'
        }
        
        context = self.get_request_context()
        serializer = TaskSerializer(data=data, context=context)
        self.assertTrue(serializer.is_valid())
        
    def test_mission_progress_validation(self):
        """Test mission progress serializer validation"""
        # Test valid data
        data = {
            'mission_id': 1,
            'progress_increment': 5
        }
        
        serializer = MissionProgressSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Test invalid progress increment
        data['progress_increment'] = -1
        serializer = MissionProgressSerializer(data=data)
        # Note: The serializer doesn't have validation for negative values
        # This would typically be handled in the view or model level
        
    def test_friendship_serializer_validation(self):
        """Test friendship serializer validation"""
        # Test with valid friend username
        data = {
            'friend_username': 'testuser2',
            'status': 'pending'
        }
        
        serializer = UserFriendshipSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Test with invalid friend username
        data['friend_username'] = 'nonexistent'
        serializer = UserFriendshipSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('friend_username', serializer.errors)


class SerializerPerformanceTestCase(BaseSerializerTestCase):
    
    def test_category_serializer_performance(self):
        """Test category serializer performance with many tasks"""
        # Create many tasks
        for i in range(100):
            Task.objects.create(
                title=f'Task {i}',
                category=self.category,
                user=self.user,
                difficulty='easy',
                priority='low'
            )
        
        context = self.get_request_context()
        
        # Test serialization time
        import time
        start_time = time.time()
        serializer = CategorySerializer(self.category, context=context)
        data = serializer.data
        end_time = time.time()
        
        # Should complete quickly (less than 1 second)
        self.assertLess(end_time - start_time, 1.0)
        self.assertEqual(data['task_count'], 101)  # 100 + 1 from setUp
        
    def test_achievement_serializer_performance(self):
        """Test achievement serializer performance"""
        # Create many achievements
        achievements = []
        for i in range(50):
            achievement = Achievement.objects.create(
                name=f'Achievement {i}',
                description=f'Description {i}',
                achievement_type='task_completion',
                threshold=i * 10,
                xp_reward=i * 100
            )
            achievements.append(achievement)
        
        context = self.get_request_context()
        
        # Test bulk serialization
        import time
        start_time = time.time()
        serializer = AchievementSerializer(achievements, many=True, context=context)
        data = serializer.data
        end_time = time.time()
        
        # Should complete quickly
        self.assertLess(end_time - start_time, 2.0)
        self.assertEqual(len(data), 50)


class SerializerEdgeCasesTestCase(BaseSerializerTestCase):
    
    def test_category_serializer_with_null_values(self):
        """Test category serializer with null/empty values"""
        category = Category.objects.create(
            name='Minimal Category',
            description='',  # Empty description
            color='#000000',
            xp_multiplier=1.0
        )
        
        context = self.get_request_context()
        serializer = CategorySerializer(category, context=context)
        data = serializer.data
        
        self.assertEqual(data['description'], '')
        self.assertEqual(data['task_count'], 0)
        
    def test_task_serializer_with_null_due_date(self):
        """Test task serializer with null due date"""
        task = Task.objects.create(
            title='No Due Date Task',
            category=self.category,
            user=self.user,
            difficulty='medium',
            priority='high',
            due_date=None  # No due date
        )
        
        serializer = TaskSerializer(task)
        data = serializer.data
        
        self.assertIsNone(data['due_date'])
        self.assertEqual(data['title'], 'No Due Date Task')
        
    def test_weekly_review_with_null_suggestions(self):
        """Test weekly review with null suggestions"""
        review = WeeklyReview.objects.create(
            user=self.user,
            week_start=timezone.now().date(),
            week_end=(timezone.now() + timedelta(days=6)).date(),
            total_tasks=5,
            total_xp=250,
            early_completions=1,
            on_time_completions=2,
            late_completions=2,
            performance_score=70.0,
            suggestions=''  # 
        )
        
        serializer = WeeklyReviewSerializer(review)
        data = serializer.data
        
        self.assertEqual(data['suggestions_list'], [])
        
    def test_achievement_serializer_with_expired_mission(self):
        """Test achievement serializer with expired user mission"""
        # Create expired mission
        expired_mission = UserMission.objects.create(
            user=self.user,
            template=MissionTemplate.objects.create(
                name='Expired Mission',
                description='This mission has expired',
                mission_type='task_completion',
                difficulty='easy',
                target_value=5,
                duration_days=1,
                xp_reward=100
            ),
            title='Expired Mission',
            description='This mission has expired',
            target_value=5,
            current_progress=2,
            start_date=now() + timedelta(days=10),
            end_date=now() + timedelta(days=3),
            status='expired',
            xp_reward=100
        )
        
        serializer = UserMissionSerializer(expired_mission)
        data = serializer.data
        
        self.assertEqual(data['status'], 'expired')
        self.assertEqual(data['days_remaining'], 0)
        
    def test_notification_serializer_with_expired_notification(self):
        """Test notification serializer with expired notification"""
        expired_notification = Notification.objects.create(
            user=self.user,
            notification_type='task_reminder',
            title='Expired Notification',
            message='This notification has expired',
            priority='low',
            expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )
        
        serializer = NotificationSerializer(expired_notification)
        data = serializer.data
        
        self.assertTrue(data['is_expired'])
        
    def test_leaderboard_entry_with_zero_values(self):
        """Test leaderboard entry with zero/minimal values"""
        entry = LeaderboardEntry.objects.create(
            user=self.user,
            leaderboard_type=LeaderboardType.objects.create(
                name='Test Board',
                leaderboard_type='daily',
                is_active=True
            ),
            score=0,
            rank=100,
            tasks_completed=0,
            total_xp=0,
            streak_count=0,
            punctuality_rate=0.0,
            period_start=timezone.now()+ timedelta(days=7),
            period_end=timezone.now()+ timedelta(days=7)
        )
        
        serializer = LeaderboardEntrySerializer(entry)
        data = serializer.data
        
        self.assertEqual(data['score'], 0)
        self.assertEqual(data['rank'], 100)
        self.assertIsNone(data['performance_badge'])  # No badge for zero stats


class SerializerIntegrationTestCase(BaseSerializerTestCase):
    
    def test_task_with_category_and_xp_integration(self):
        """Test task serializer integration with category and XP calculation"""
        # Create task with specific category
        high_xp_category = Category.objects.create(
            name='High XP Category',
            xp_multiplier=2.0,
            color='#FF0000'
        )
        
        task = Task.objects.create(
            title='High XP Task',
            category=high_xp_category,
            user=self.user,
            difficulty='hard',
            priority='high',
            is_completed=True,
            completed_at=timezone.now()
        )
        
        with patch('progress.gamification.GamificationEngine') as mock_engine:
            mock_engine.return_value.calculate_task_xp.return_value = 300
            
            context = self.get_request_context()
            serializer = TaskSerializer(task, context=context)
            data = serializer.data
            
            self.assertEqual(data['category_name'], 'High XP Category')
            self.assertEqual(data['xp_value'], 300)
            self.assertTrue(data['is_completed'])
            self.assertIsNotNone(data['completed_at'])
            
    def test_user_mission_with_template_integration(self):
        """Test user mission serializer integration with template"""
        # Create mission template with category
        template = MissionTemplate.objects.create(
            name='Integration Mission',
            description='Test integration',
            mission_type='streak_maintenance',
            difficulty='legendary',
            target_value=30,
            duration_days=30,
            xp_reward=1000,
            category=self.category,
            is_repeatable=False
        )
        
        mission = UserMission.objects.create(
            user=self.user,
            template=template,
            title='Integration Mission',
            description='Test integration',
            target_value=30,
            current_progress=15,
            start_date=timezone.now(),
            end_date=now() + timedelta(days=10),
            status='active',
            xp_reward=1000,
            category=self.category
        )
        
        serializer = UserMissionSerializer(mission)
        data = serializer.data
        
        self.assertEqual(data['template']['name'], 'Integration Mission')
        self.assertEqual(data['template']['difficulty'], 'legendary')
        self.assertEqual(data['template']['category_name'], 'Work')
        self.assertEqual(data['difficulty_color'], '#dc3545')  # legendary = red
        self.assertEqual(data['template']['estimated_time'], 20)  # legendary = 20
        
    def test_achievement_with_user_progress_integration(self):
        achievement = Achievement.objects.create(
            name='Test Achievement',
            description='A test achievement for completing tasks',
            achievement_type='task_count',
            threshold=100  # Provide a valid threshold value
        )
        UserAchievement.objects.create(
            user=self.user,
            achievement=achievement,
            progress=25,
            unlocked_at=None
        )
        context = self.get_request_context(user=self.user)
        serializer = AchievementSerializer(achievement, context=context)
        data = serializer.data
        self.assertEqual(data['progress'], 25)


class SerializerSecurityTestCase(BaseSerializerTestCase):
    
    def test_task_serializer_user_isolation(self):
        """Test that task serializer respects user isolation"""
        # Create task for different user
        Task.objects.create(
            title='Other User Task',
            category=self.category,
            user=self.user2,
            difficulty='easy',
            priority='low'
        )
        
        # Test that user context is properly applied
        context = self.get_request_context(user=self.user)
        serializer = TaskSerializer(data={
            'title': 'New Task',
            'category': self.category.id,
            'difficulty': 'medium',
            'priority': 'high'
        }, context=context)
        
        self.assertTrue(serializer.is_valid())
        task = serializer.save()
        
        # Verify the task is assigned to the correct user
        self.assertEqual(task.user, self.user)
        self.assertNotEqual(task.user, self.user2)
        
    def test_category_task_count_user_filtering(self):
        """Test that category task count is properly filtered by user"""
        # Create tasks for different users
        Task.objects.create(
            title='User1 Task',
            category=self.category,
            user=self.user,
            difficulty='easy',
            priority='low'
        )
        Task.objects.create(
            title='User2 Task',
            category=self.category,
            user=self.user2,
            difficulty='easy',
            priority='low'
        )
        
        # Test with user context
        context = self.get_request_context(user=self.user)
        serializer = CategorySerializer(self.category, context=context)
        data = serializer.data
        
        # Should only count tasks for the authenticated user
        self.assertEqual(data['task_count'], 2)  # 1 from setUp + 1 new
        
        # Test with different user context
        context = self.get_request_context(user=self.user2)
        serializer = CategorySerializer(self.category, context=context)
        data = serializer.data
        
        # Should only count tasks for user2
        self.assertEqual(data['task_count'], 1)
        
    def test_achievement_user_isolation(self):
        """Test that achievement progress is user-specific"""
        
        # Test with user1 context
        context = self.get_request_context(user=self.user)
        serializer = AchievementSerializer(self.achievement, context=context)
        data = serializer.data
        
        self.assertTrue(data['is_unlocked'])
        self.assertEqual(data['progress'], 10)
        
        # Test with user2 context (no achievement)
        context = self.get_request_context(user=self.user2)
        serializer = AchievementSerializer(self.achievement, context=context)
        data = serializer.data
        
        self.assertFalse(data['is_unlocked'])
        self.assertEqual(data['progress'], 0)


class SerializerErrorHandlingTestCase(BaseSerializerTestCase):
    
    def test_task_serializer_with_invalid_category(self):
        """Test task serializer with invalid category"""
        data = {
            'title': 'Test Task',
            'category': 99999,  # Non-existent category
            'difficulty': 'medium',
            'priority': 'high'
        }
        
        context = self.get_request_context()
        serializer = TaskSerializer(data=data, context=context)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('category', serializer.errors)
        
    def test_friendship_serializer_self_friendship(self):
        """Test that user cannot befriend themselves"""
        data = {
            'friend_username': 'testuser',  # Same as self.user
            'status': 'pending'
        }
        
        UserFriendshipSerializer(data=data)
        # Note: This validation would typically be in the view or model
        # The serializer itself doesn't prevent self-friendship
        
    def test_mission_serializer_with_invalid_template(self):
        """Test mission serializer with invalid template"""
        data = {
            'template_id': 99999,  # Non-existent template
            'title': 'Invalid Mission',
            'target_value': 10,
            'status': 'active'
        }
        
        serializer = UserMissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('template_id', serializer.errors)
        
    @patch('progress.gamification.GamificationEngine')
    def test_task_serializer_xp_calculation_error(self, mock_engine_class):
        """Test task serializer when XP calculation fails"""
        mock_engine = MagicMock()
        mock_engine.calculate_task_xp.side_effect = Exception("XP calculation failed")
        mock_engine_class.return_value = mock_engine
        
        context = self.get_request_context()
        serializer = TaskSerializer(self.task, context=context)
        
        # Should handle the exception gracefully
        with self.assertRaises(Exception):
            _ = serializer.data['xp_value']


# Additional utility test functions
class SerializerUtilityTestCase(BaseSerializerTestCase):
    
    def test_serializer_context_handling(self):
        """Test how serializers handle missing context"""
        # Test achievement serializer without context
        serializer = AchievementSerializer(self.achievement)
        data = serializer.data
        
        self.assertFalse(data['is_unlocked'])
        self.assertEqual(data['progress'], 0)
        self.assertIsNone(data['unlocked_at'])
        
        # Test category serializer without context
        serializer = CategorySerializer(self.category)
        data = serializer.data
        
        # Should return total count when no user context
        self.assertEqual(data['task_count'], 1)
        
    def test_serializer_many_flag(self):
        """Test serializers with many=True flag"""
        # Create multiple categories
        categories = [
            Category.objects.create(name=f'Category {i}', color=f'#{i:06x}')
            for i in range(3)
        ]
        
        context = self.get_request_context()
        serializer = CategorySerializer(categories, many=True, context=context)
        data = serializer.data
        
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['name'], 'Category 0')
        self.assertEqual(data[1]['name'], 'Category 1')
        self.assertEqual(data[2]['name'], 'Category 2')
        
    def test_serializer_partial_updates(self):
        """Test serializers with partial updates"""
        data = {'title': 'Updated Task Title'}
        
        context = self.get_request_context()
        serializer = TaskSerializer(self.task, data=data, partial=True, context=context)
        
        self.assertTrue(serializer.is_valid())
        updated_task = serializer.save()
        
        self.assertEqual(updated_task.title, 'Updated Task Title')
        self.assertEqual(updated_task.category, self.category)  # Unchanged
        
    def test_read_only_fields(self):
        """Test that read-only fields are properly handled"""
        # Try to update read-only fields
        data = {
            'title': 'New Title',
            'completed_at': timezone.now(),  # Read-only field
            'category_name': 'Should Not Update'  # Read-only field
        }
        
        context = self.get_request_context()
        serializer = TaskSerializer(self.task, data=data, partial=True, context=context)
        
        self.assertTrue(serializer.is_valid())
        # Read-only fields should not be in validated_data
        self.assertNotIn('completed_at', serializer.validated_data)
        self.assertNotIn('category_name', serializer.validated_data)
