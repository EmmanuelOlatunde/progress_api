
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from unittest.mock import patch, MagicMock

from ..models import (
    Category, Task,  ProgressProfile, Achievement, UserAchievement,
    WeeklyReview, MissionTemplate, UserMission, LeaderboardType,
    LeaderboardEntry, UserFriendship, Notification,
    UserNotificationSettings, SystemSetting
)

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test Category model"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name="Work",
            description="Work related tasks",
            color="#FF5733",
            xp_multiplier=1.5
        )
    
    def test_category_creation(self):
        """Test category creation with all fields"""
        self.assertEqual(self.category.name, "Work")
        self.assertEqual(self.category.description, "Work related tasks")
        self.assertEqual(self.category.color, "#FF5733")
        self.assertEqual(self.category.xp_multiplier, 1.5)
        self.assertTrue(self.category.created_at)
    
    def test_category_str_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.category), "Work")
    
    def test_category_unique_name(self):
        """Test name uniqueness constraint"""
        with self.assertRaises(Exception):
            Category.objects.create(name="Work")
    
    def test_category_defaults(self):
        """Test default values"""
        cat = Category.objects.create(name="Personal")
        self.assertEqual(cat.color, "#007bff")
        self.assertEqual(cat.xp_multiplier, 1.0)
        self.assertEqual(cat.description, "")


class TaskModelTest(TestCase):
    """Test Task model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Work",
            xp_multiplier=1.2
        )
        self.task = Task.objects.create(
            user=self.user,
            title="Complete project",
            description="Finish the Django project",
            category=self.category,
            difficulty="medium",
            priority="high",
            due_date=timezone.now() + timedelta(days=3)
        )
    
    def test_task_creation(self):
        """Test task creation"""
        self.assertEqual(self.task.title, "Complete project")
        self.assertEqual(self.task.user, self.user)
        self.assertEqual(self.task.category, self.category)
        self.assertEqual(self.task.difficulty, "medium")
        self.assertEqual(self.task.priority, "high")
        self.assertFalse(self.task.is_completed)
        self.assertIsNone(self.task.completed_at)
    
    def test_task_str_representation(self):
        """Test string representation"""
        expected = f"{self.task.title} ({self.task.get_difficulty_display()})"
        self.assertEqual(str(self.task), expected)
    
    def test_task_defaults(self):
        """Test default values"""
        task = Task.objects.create(
            user=self.user,
            title="Simple task",
            category=self.category
        )
        self.assertEqual(task.difficulty, "medium")
        self.assertEqual(task.priority, "medium")
        self.assertFalse(task.is_completed)
    
    @patch('progress.gamification.GamificationEngine')
    def test_complete_task_success(self, mock_engine_class):
        mock_engine = MagicMock()
        mock_engine.can_complete_task.return_value = (True, "Can complete")
        mock_engine.award_task_xp.return_value = (100, "Earned 100 XP")
        mock_engine_class.return_value = mock_engine

        self.task.created_at = timezone.now() - timedelta(hours=2)  # Ensure it passes time check
        self.task.save()

        success, message = self.task.complete_task()

        self.assertTrue(success)
        self.assertEqual(message, "Earned 100 XP")
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completed_at)

        
    @patch('progress.gamification')
    def test_complete_task_already_completed(self, mock_engine_class):
        """Test completing already completed task"""
        self.task.is_completed = True
        self.task.save()
        
        success, message = self.task.complete_task()
        
        self.assertFalse(success)
        self.assertEqual(message, "Task is already completed")
    
    @patch('progress.gamification')
    def test_complete_task_cannot_complete(self, mock_engine_class):
        """Test task that cannot be completed"""
        mock_engine = MagicMock()
        mock_engine.can_complete_task.return_value = (False, "Too early to complete")
        mock_engine_class.return_value = mock_engine
        
        success, message = self.task.complete_task()
        
        self.assertFalse(success)
        #self.assertEqual(message, "Task created too recently. Wait 59 minutes before completing this medium task.")
        self.assertFalse(self.task.is_completed)
    
    def test_get_timing_info_no_deadline(self):
        """Test timing info for task without deadline"""
        task = Task.objects.create(
            user=self.user,
            title="No deadline task",
            category=self.category
        )
        
        timing_info = task.get_timing_info()
        
        self.assertEqual(timing_info['status'], 'no_deadline')
        self.assertEqual(timing_info['message'], 'No deadline set')
        self.assertTrue(timing_info['can_complete'])
    
    def test_get_timing_info_completed_on_time(self):
        """Test timing info for task completed on time"""
        past_due = timezone.now() - timedelta(days=1)
        self.task.due_date = past_due
        self.task.is_completed = True
        self.task.completed_at = past_due - timedelta(hours=1)
        self.task.save()
        
        timing_info = self.task.get_timing_info()
        
        self.assertEqual(timing_info['status'], 'completed_on_time')
        self.assertEqual(timing_info['message'], 'Completed on time')
    
    def test_get_timing_info_completed_late(self):
        """Test timing info for task completed late"""
        past_due = timezone.now() - timedelta(days=2)
        self.task.due_date = past_due
        self.task.is_completed = True
        self.task.completed_at = timezone.now() - timedelta(days=1)
        self.task.save()
        
        timing_info = self.task.get_timing_info()
        
        self.assertEqual(timing_info['status'], 'completed_late')
        self.assertIn('late', timing_info['message'])
    
    def test_get_timing_info_overdue(self):
        """Test timing info for overdue task"""
        self.task.due_date = timezone.now() - timedelta(days=1)
        self.task.save()
        
        timing_info = self.task.get_timing_info()
        
        self.assertEqual(timing_info['status'], 'overdue')
        self.assertIn('Overdue', timing_info['message'])


class ProgressProfileModelTest(TestCase):
    """Test ProgressProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.progress_profile
        self.profile.total_xp=750
        self.profile.current_level=3
        self.profile.current_streak=5
        self.profile.longest_streak=8
        self.profile.total_early_completions=10
        self.profile.total_on_time_completions=15
        self.profile.total_late_completions=5
        self.profile.save()
        
    
    def test_progress_profile_creation(self):
        """Test progress profile creation"""
        self.assertEqual(self.user.progress_profile.user, self.user)
        self.assertEqual(self.user.progress_profile.total_xp, 750)
        self.assertEqual(self.user.progress_profile.current_level, 3)
        self.assertEqual(self.user.progress_profile.current_streak, 5)
    
    def test_progress_profile_str_representation(self):
        """Test string representation"""
        expected = f"{self.user.username} - Level {self.profile.current_level}"
        self.assertEqual(str(self.profile), expected)
    
    def test_xp_calculations(self):
        """Test XP calculation properties"""
        self.assertEqual(self.user.progress_profile.xp_for_current_level, 500)
        self.assertEqual(self.user.progress_profile.xp_for_next_level, 900)
        self.assertEqual(self.user.progress_profile.xp_progress_in_current_level, 250)
        self.assertEqual(self.user.progress_profile.xp_needed_for_next_level, 150)

    
    def test_progress_percentage(self):
        """Test progress percentage calculation"""
        # Progress in level 3: 250 XP out of 400 XP needed = 62.5%
        expected_percentage = (250 / 400) * 100
        self.assertEqual(self.user.progress_profile.progress_percentage, expected_percentage)
    
    def test_calculate_xp_for_level(self):
        """Test XP calculation for specific levels"""
        self.assertEqual(self.user.progress_profile.calculate_xp_for_level(1), 0)
        self.assertEqual(self.user.progress_profile.calculate_xp_for_level(2), 200)
        self.assertEqual(self.user.progress_profile.calculate_xp_for_level(3), 500)
        self.assertEqual(self.user.progress_profile.calculate_xp_for_level(4), 900)
    
    @patch('progress.gamification.GamificationEngine')
    def test_update_level(self, mock_engine_class):
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        self.profile.current_level = 2
        self.profile.total_xp = 1200  # Must exceed level 2 threshold
        self.profile.save()

        self.profile.update_level()

        self.assertEqual(self.profile.current_level, 4)  # or appropriate level
        mock_engine.check_level_achievements.assert_called_once()


    def test_punctuality_rate(self):
        """Test punctuality rate calculation"""
        # 10 early + 15 on time out of 30 total = 83.33%
        expected_rate = int(((10 + 15) / 30) * 100)
        self.assertEqual(self.user.progress_profile.punctuality_rate(), expected_rate)
    
    def test_punctuality_rate_no_tasks(self):
        """Test punctuality rate with no completed tasks"""
        profile = self.user.progress_profile
        profile.total_early_completions = 0
        profile.total_on_time_completions = 0
        profile.total_late_completions = 0
        profile.save()
        self.assertEqual(profile.punctuality_rate(), 100)


class AchievementModelTest(TestCase):
    """Test Achievement and UserAchievement models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.achievement = Achievement.objects.create(
            name="Task Master",
            description="Complete 100 tasks",
            achievement_type="task_count",
            icon="🏆",
            threshold=100,
            xp_reward=500
        )
    
    def test_achievement_creation(self):
        """Test achievement creation"""
        self.assertEqual(self.achievement.name, "Task Master")
        self.assertEqual(self.achievement.achievement_type, "task_count")
        self.assertEqual(self.achievement.threshold, 100)
        self.assertEqual(self.achievement.xp_reward, 500)
        self.assertFalse(self.achievement.is_hidden)
    
    def test_achievement_str_representation(self):
        """Test string representation"""
        expected = f"{self.achievement.name} ({self.achievement.get_achievement_type_display()})"
        self.assertEqual(str(self.achievement), expected)
    
    def test_user_achievement_creation(self):
        """Test user achievement creation"""
        user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement,
            progress=50
        )
        
        self.assertEqual(user_achievement.user, self.user)
        self.assertEqual(user_achievement.achievement, self.achievement)
        self.assertEqual(user_achievement.progress, 50)
        self.assertIsNotNone(user_achievement.unlocked_at)
    
    def test_user_achievement_unique_constraint(self):
        """Test unique constraint on user-achievement pair"""
        UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement
        )
        
        with self.assertRaises(Exception):
            UserAchievement.objects.create(
                user=self.user,
                achievement=self.achievement
            )


class WeeklyReviewModelTest(TestCase):
    """Test WeeklyReview model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.review = WeeklyReview.objects.create(
            user=self.user,
            week_start=date(2024, 1, 1),
            week_end=date(2024, 1, 7),
            total_tasks=20,
            total_xp=500,
            early_completions=8,
            on_time_completions=10,
            late_completions=2,
            performance_score=85,
            category_breakdown={"work": 12, "personal": 8}
        )
    
    def test_weekly_review_creation(self):
        """Test weekly review creation"""
        self.assertEqual(self.review.total_tasks, 20)
        self.assertEqual(self.review.total_xp, 500)
        self.assertEqual(self.review.performance_score, 85)
        self.assertEqual(self.review.category_breakdown["work"], 12)
    
    def test_completion_rate(self):
        """Test completion rate calculation"""
        # 18 completed out of 20 total = 90%
        expected_rate = int(((8 + 10) / 20) * 100)
        self.assertEqual(self.review.completion_rate, expected_rate)
    
    def test_punctuality_score(self):
        """Test punctuality score calculation"""
        # (8*2 + 10*1) / (20*2) = 26/40 = 65%
        expected_score = int(((8 * 2 + 10) / (20 * 2)) * 100)
        self.assertEqual(self.review.punctuality_score, expected_score)
    
    def test_performance_grade(self):
        """Test performance grade calculation"""
        self.assertEqual(self.review.performance_grade, 'A')
        
        # Test different grades
        self.review.performance_score = 95
        self.assertEqual(self.review.performance_grade, 'A+')
        
        self.review.performance_score = 75
        self.assertEqual(self.review.performance_grade, 'B')
        
        self.review.performance_score = 55
        self.assertEqual(self.review.performance_grade, 'F')


class MissionModelTest(TestCase):
    """Test Mission-related models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name="Work")
        self.mission_template = MissionTemplate.objects.create(
            name="Weekly Warrior",
            description="Complete 10 tasks this week",
            mission_type="task_count",
            difficulty="medium",
            target_value=10,
            duration_days=7,
            xp_reward=200,
            category=self.category
        )
        self.user_mission = UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title="Weekly Warrior",
            description="Complete 10 tasks this week",
            target_value=10,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=200,
            category=self.category
        )
    
    def test_mission_template_creation(self):
        """Test mission template creation"""
        self.assertEqual(self.mission_template.name, "Weekly Warrior")
        self.assertEqual(self.mission_template.mission_type, "task_count")
        self.assertEqual(self.mission_template.target_value, 10)
        self.assertEqual(self.mission_template.xp_reward, 200)
    
    def test_user_mission_creation(self):
        """Test user mission creation"""
        self.assertEqual(self.user_mission.user, self.user)
        self.assertEqual(self.user_mission.template, self.mission_template)
        self.assertEqual(self.user_mission.status, 'active')
        self.assertEqual(self.user_mission.current_progress, 0)
    
    def test_mission_progress_percentage(self):
        """Test progress percentage calculation"""
        self.user_mission.current_progress = 5
        self.assertEqual(self.user_mission.progress_percentage, 50)
        
        self.user_mission.current_progress = 12
        self.assertEqual(self.user_mission.progress_percentage, 100)
    
    def test_mission_is_expired(self):
        """Test mission expiration check"""
        self.user_mission.end_date = timezone.now() - timedelta(days=1)
        self.assertTrue(self.user_mission.is_expired)
        
        self.user_mission.end_date = timezone.now() + timedelta(days=1)
        self.assertFalse(self.user_mission.is_expired)
    
    def test_mission_time_remaining(self):
        """Test time remaining calculation"""
        future_date = timezone.now() + timedelta(days=2)
        self.user_mission.end_date = future_date
        time_remaining = self.user_mission.time_remaining
        
        self.assertIsNotNone(time_remaining)
        self.assertGreater(time_remaining.total_seconds(), 0)
    
    def test_update_progress(self):
        """Test mission progress update"""
        success = self.user_mission.update_progress(3)
        self.assertTrue(success)
        self.assertEqual(self.user_mission.current_progress, 3)
    

    @patch('progress.models.Notification.objects.create')
    @patch('progress.gamification.MissionService._award_mission_rewards')  # patch the internal logic
    def test_complete_mission(self, mock_award, mock_notify):
        result = self.user_mission.complete_mission()
        self.assertTrue(result)

        mock_award.assert_called_once_with(self.user_mission)
        mock_notify.assert_called_once_with(
            user=self.user_mission.user,
            notification_type='mission_completed',
            title='Mission Completed!',
            message=f'You completed "{self.user_mission.title}" and earned {self.user_mission.xp_reward} XP!',
            data={'mission_id': self.user_mission.id, 'xp_earned': self.user_mission.xp_reward}
        )



class NotificationModelTest(TestCase):
    """Test Notification-related models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type='task_reminder',
            title='Task Due Soon',
            message='You have a task due in 2 hours',
            priority='high',
            data={'task_id': 123}
        )
    
    def test_notification_creation(self):
        """Test notification creation"""
        self.assertEqual(self.notification.user, self.user)
        self.assertEqual(self.notification.notification_type, 'task_reminder')
        self.assertEqual(self.notification.title, 'Task Due Soon')
        self.assertEqual(self.notification.priority, 'high')
        self.assertFalse(self.notification.is_read)
        self.assertEqual(self.notification.data['task_id'], 123)
    
    def test_notification_mark_as_read(self):
        """Test marking notification as read"""
        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)
        
        self.notification.mark_as_read()
        
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)
    
    def test_notification_archive(self):
        """Test archiving notification"""
        self.assertFalse(self.notification.is_archived)
        
        self.notification.archive()
        
        self.assertTrue(self.notification.is_archived)
    
    def test_notification_is_expired(self):
        """Test notification expiration check"""
        self.notification.expires_at = timezone.now() - timedelta(hours=1)
        self.assertTrue(self.notification.is_expired)
        
        self.notification.expires_at = timezone.now() + timedelta(hours=1)
        self.assertFalse(self.notification.is_expired)
    
    def test_user_notification_settings(self):
        """Test user notification settings"""
        settings = UserNotificationSettings.objects.create(
            user=self.user,
            email_notifications=True,
            push_notifications=False,
            reminder_frequency='daily'
        )
        
        self.assertEqual(settings.user, self.user)
        self.assertTrue(settings.email_notifications)
        self.assertFalse(settings.push_notifications)
        self.assertEqual(settings.reminder_frequency, 'daily')


class SystemSettingModelTest(TestCase):
    """Test SystemSetting model"""
    
    def test_system_setting_creation(self):
        """Test system setting creation"""
        setting = SystemSetting.objects.create(
            key='max_daily_tasks',
            value='50',
            description='Maximum tasks per day',
            data_type='integer'
        )
        
        self.assertEqual(setting.key, 'max_daily_tasks')
        self.assertEqual(setting.value, '50')
        self.assertEqual(setting.data_type, 'integer')
    
    def test_system_setting_get_value_types(self):
        """Test getting values in correct data types"""
        # Integer
        int_setting = SystemSetting.objects.create(
            key='max_tasks', value='100', data_type='integer'
        )
        self.assertEqual(int_setting.get_value(), 100)
        self.assertIsInstance(int_setting.get_value(), int)
        
        # Float
        float_setting = SystemSetting.objects.create(
            key='xp_multiplier', value='1.5', data_type='float'
        )
        self.assertEqual(float_setting.get_value(), 1.5)
        self.assertIsInstance(float_setting.get_value(), float)
        
        # Boolean
        bool_setting = SystemSetting.objects.create(
            key='notifications_enabled', value='true', data_type='boolean'
        )
        self.assertTrue(bool_setting.get_value())
        self.assertIsInstance(bool_setting.get_value(), bool)
        
        # JSON
        json_setting = SystemSetting.objects.create(
            key='config', value='{"theme": "dark", "lang": "en"}', data_type='json'
        )
        expected_json = {"theme": "dark", "lang": "en"}
        self.assertEqual(json_setting.get_value(), expected_json)
        self.assertIsInstance(json_setting.get_value(), dict)
        
        # String (default)
        str_setting = SystemSetting.objects.create(
            key='app_name', value='TaskMaster', data_type='string'
        )
        self.assertEqual(str_setting.get_value(), 'TaskMaster')
        self.assertIsInstance(str_setting.get_value(), str)


class LeaderboardModelTest(TestCase):
    """Test Leaderboard-related models"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1', email='user1@example.com', password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2', email='user2@example.com', password='pass123'
        )
        self.leaderboard_type = LeaderboardType.objects.create(
            name='Weekly XP',
            leaderboard_type='weekly',
            description='Weekly XP leaderboard',
            reset_frequency='weekly'
        )
    
    def test_leaderboard_type_creation(self):
        """Test leaderboard type creation"""
        self.assertEqual(self.leaderboard_type.name, 'Weekly XP')
        self.assertEqual(self.leaderboard_type.leaderboard_type, 'weekly')
        self.assertEqual(self.leaderboard_type.reset_frequency, 'weekly')
        self.assertTrue(self.leaderboard_type.is_active)
    
    def test_leaderboard_entry_creation(self):
        """Test leaderboard entry creation"""
        start_date = timezone.now() - timedelta(days=7)
        end_date = timezone.now()
        
        entry = LeaderboardEntry.objects.create(
            leaderboard_type=self.leaderboard_type,
            user=self.user1,
            score=1500,
            rank=1,
            period_start=start_date,
            period_end=end_date,
            tasks_completed=25,
            total_xp=1500,
            punctuality_rate=85.5
        )
        
        self.assertEqual(entry.user, self.user1)
        self.assertEqual(entry.score, 1500)
        self.assertEqual(entry.rank, 1)
        self.assertEqual(entry.tasks_completed, 25)
        self.assertEqual(entry.punctuality_rate, 85.5)
    
    def test_user_friendship_creation(self):
        """Test user friendship creation"""
        friendship = UserFriendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status='accepted'
        )
        
        self.assertEqual(friendship.user, self.user1)
        self.assertEqual(friendship.friend, self.user2)
        self.assertEqual(friendship.status, 'accepted')


# Integration Tests
class IntegrationTest(TestCase):
    """Integration tests for model interactions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name="Work",
            xp_multiplier=1.5
        )
        self.profile  = self.user.profile 
        self.progress_profile = self.user.progress_profile
        self.profile.total_xp=100
        
    
    def test_task_category_relationship(self):
        """Test task-category relationship"""
        task = Task.objects.create(
            user=self.user,
            title="Test task",
            category=self.category
        )
        
        # Test reverse relationship
        self.assertEqual(self.category.tasks.count(), 1)
        self.assertEqual(self.category.tasks.first(), task)
    
    def test_user_task_relationship(self):
        """Test user-task relationship"""
        Task.objects.create(
            user=self.user,
            title="Task 1",
            category=self.category
        )
        Task.objects.create(
            user=self.user,
            title="Task 2",
            category=self.category
        )
        
        # Test reverse relationship
        self.assertEqual(self.user.tasks.count(), 2)
        self.assertEqual(
            list(self.user.tasks.order_by('title').values_list('title', flat=True)),
            ['Task 1', 'Task 2']
        )
    
    def test_user_progress_profile_relationship(self):
        """Test user-progress profile one-to-one relationship"""
        self.assertEqual(self.progress_profile.user, self.profile.user)
        self.assertEqual(self.profile.user, self.user)
    
    def test_cascade_deletion(self):
        """Test cascade deletion behavior"""
        Task.objects.create(
            user=self.user,
            title="Test task",
            category=self.category
        )
        
        # Delete user should delete tasks and profile
        user_id = self.user.id
        self.user.delete()
        
        # Check that related objects are deleted
        self.assertFalse(Task.objects.filter(user_id=user_id).exists())
        self.assertFalse(ProgressProfile.objects.filter(user_id=user_id).exists())
        
        # Category should still exist
        self.assertTrue(Category.objects.filter(id=self.category.id).exists())

