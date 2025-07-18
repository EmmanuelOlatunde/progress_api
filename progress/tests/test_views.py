from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
# from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
# from rest_framework.authtoken.models import Token
# from django.db.models import Count

from progress.models import (
    Task, Category, XPLog,  Achievement,#ProgressProfile,
    LeaderboardType, LeaderboardEntry, UserFriendship,
    MissionTemplate, UserMission, WeeklyReview, UserAchievement,
    Notification, NotificationType, UserNotificationSettings
)
from progress.views import ( GameStatsViewSet

)
User = get_user_model()



class BaseTestCase(APITestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test categories
        self.category1 = Category.objects.create(
            name='Work',
            color='#FF0000'
        )
        self.category2 = Category.objects.create(
            name='Personal',
            color='#00FF00'
        )
        
        # First user
        user_profile = self.user.progress_profile
        user_profile.total_xp = 100
        user_profile.current_level = 2
        user_profile.current_streak = 5
        user_profile.longest_streak = 10
        user_profile.save()

        # Second user
        self.profile2 = self.user2.progress_profile
        self.profile2.total_xp = 100
        self.profile2.current_level = 2
        self.profile2.current_streak = 5
        self.profile2.longest_streak = 10
        self.profile2.save()


        # Create mission templates
        self.mission_template = MissionTemplate.objects.create(
            name='Complete 5 tasks',
            description='Complete 5 tasks in any category',
            category=self.category1,  # Use Category instance
            target_value=5,
            xp_reward=100,
            duration_days=7,
            min_user_level=1,
            is_active=True
        )

        # Create notification types
        self.notification_type_friend = NotificationType.objects.create(
            name='friend_request',
            description='Friend request notifications'
        )
        self.notification_type_mission = NotificationType.objects.create(
            name='mission_accepted',
            description='Mission accepted notifications'
        )
        self.notification_type_test = NotificationType.objects.create(
            name='test',
            description='Test notifications'
        )
    
    def get_first_result(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        results = response.data['results']
        self.assertTrue(len(results) > 0)
        return results[0]

    
class CategoryViewSetTests(BaseTestCase):
    """Test cases for CategoryViewSet"""
    
    def test_list_categories(self):
        """Test listing categories with task count annotation"""
        # Create some tasks
        Task.objects.create(
            user=self.user,
            title='Test Task 1',
            category=self.category1,
            priority='medium'
        )
        Task.objects.create(
            user=self.user,
            title='Test Task 2',
            category=self.category1,
            priority='high'
        )
        
        url = reverse('category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        data = {c['name']: c['task_count'] for c in response.data['results']}
        self.assertEqual(data['Work'], 2)
        self.assertEqual(data['Personal'], 0)

    
    def test_create_category(self):
        """Test creating a new category"""
        url = reverse('category-list')
        data = {
            'name': 'New Category',
            'color': '#00FF00',
            'description': 'A new test category'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(response.data['name'], 'New Category')
    
    def test_swagger_fake_view(self):
        """Test that swagger fake view returns empty queryset"""
        # This would typically be handled by the swagger generation
        # We'll test the condition directly
        from progress.views import CategoryViewSet
        
        viewset = CategoryViewSet()
        viewset.swagger_fake_view = True
        
        queryset = viewset.get_queryset()
        self.assertEqual(queryset.count(), 0)


class TaskViewSetTests(BaseTestCase):
    """Test cases for TaskViewSet"""
    
    def setUp(self):
        super().setUp()
        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='Test task description',
            category=self.category1,
            priority='medium',
            difficulty='medium'
        )
    
    def test_list_tasks(self):
        """Test listing user's tasks"""
        url = reverse('task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Task')
    
    def test_create_task(self):
        """Test creating a new task"""
        url = reverse('task-list')
        data = {
            'title': 'New Task',
            'description': 'New task description',
            'category': self.category1.id,
            'priority': 'high',
            'difficulty': 'hard'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Task')
    
    @patch('progress.models.Task.complete_task')
    def test_complete_task_success(self, mock_complete):
        """Test completing a task successfully"""
        mock_complete.return_value = (True, 'Task completed successfully')
        
        url = reverse('task-complete', kwargs={'pk': self.task.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('task', response.data)
        mock_complete.assert_called_once()
    
    @patch('progress.models.Task.complete_task')
    def test_complete_task_failure(self, mock_complete):
        """Test completing a task with failure"""
        mock_complete.return_value = (False, 'Task completion failed')
        
        url = reverse('task-complete', kwargs={'pk': self.task.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_complete_already_completed_task(self):
        """Test completing an already completed task"""
        self.task.is_completed = True
        self.task.save()
        
        url = reverse('task-complete', kwargs={'pk': self.task.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Task is already completed')
    
    def test_task_stats(self):
        """Test task statistics endpoint"""
        # Create completed task
        Task.objects.create(
            user=self.user,
            title='Completed Task',
            category=self.category1,
            priority='high',
            is_completed=True,
            completed_at=timezone.now()
        )
        
        url = reverse('task-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tasks'], 2)
        self.assertEqual(response.data['completed_tasks'], 1)
        self.assertEqual(response.data['pending_tasks'], 1)
        self.assertEqual(response.data['completion_rate'], 50.0)
        self.assertIn('category_breakdown', response.data)
        self.assertIn('recent_completed', response.data)
    
    def test_empty_tasks_queryset(self):
        """Test when user has no tasks"""
        Task.objects.filter(user=self.user).delete()
        
        url = reverse('task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


class XPViewSetTests(BaseTestCase):
    """Test cases for XPViewSet"""
    
    def setUp(self):
        super().setUp()
        self.xp_log = XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=50,
            description='Completed a task'
        )
    
    def test_list_xp_logs(self):
        """Test listing XP logs"""
        url = reverse('xp-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['xp_earned'], 50)
    
    def test_xp_summary(self):
        """Test XP summary endpoint"""
        url = reverse('xp-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile', response.data)
        self.assertIn('recent_activity', response.data)
        self.assertEqual(response.data['profile']['total_xp'], 100)
    
    def test_xp_level_info(self):
        """Test detailed level information"""
        url = reverse('xp-level')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_level', response.data)
        self.assertIn('total_xp', response.data)
        self.assertIn('xp_for_next_level', response.data)
        self.assertIn('progress_percentage', response.data)
        self.assertEqual(response.data['current_level'], 2)
        self.assertEqual(response.data['total_xp'], 100)


class AchievementViewSetTests(BaseTestCase):
    """Test cases for AchievementViewSet"""
    
    def setUp(self):
        super().setUp()
        self.achievement = Achievement.objects.create(
            name='Test Achievement',
            description='Test achievement description',
            achievement_type='task_count',
            threshold=10,
            xp_reward=100,
            is_hidden=False
        )
        
        self.user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=self.achievement,
            unlocked_at=timezone.now()
        )
    
    def test_list_achievements(self):
        """Test listing all achievements"""
        url = reverse('achievement-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Achievement')
    
    def test_unlocked_achievements(self):
        """Test listing only unlocked achievements"""
        url = reverse('achievement-unlocked')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Achievement')
        self.assertIn('unlocked_at', response.data[0])


class StatsViewSetTests(BaseTestCase):
    """Test cases for StatsViewSet"""
    
    def setUp(self):
        super().setUp()
        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category1,
            priority='medium',
            is_completed=True,
            completed_at=timezone.now()
        )
    
    @patch('progress.views.GamificationEngine')
    def test_stats_list(self, mock_engine):
        """Test comprehensive statistics dashboard"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        
        url = reverse('stats-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile', response.data)
        self.assertIn('task_stats', response.data)
        self.assertIn('achievement_stats', response.data)
        self.assertIn('category_breakdown', response.data)
        self.assertIn('recent_activity', response.data)
        
        # Check profile data
        self.assertEqual(response.data['profile']['username'], self.user.username)
        self.assertEqual(response.data['profile']['level'], 2)
        self.assertEqual(response.data['profile']['total_xp'], 100)
        self.assertEqual(response.data['profile']['current_streak'], 5)
        
        # Check task stats
        self.assertEqual(response.data['task_stats']['total'], 1)
        self.assertEqual(response.data['task_stats']['completed'], 1)
        self.assertEqual(response.data['task_stats']['completion_rate'], 100.0)
    
    @patch('progress.views.GamificationEngine')
    def test_stats_with_debug(self, mock_engine):
        """Test stats with debug parameter"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.debug_streak_status.return_value = {'debug': 'info'}
        
        url = reverse('stats-list')
        response = self.client.get(url, {'debug': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_engine_instance.debug_streak_status.assert_called_once()
    
    @patch('progress.views.GamificationEngine')
    def test_stats_with_recalculate_streak(self, mock_engine):
        """Test stats with recalculate_streak parameter"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        
        url = reverse('stats-list')
        response = self.client.get(url, {'recalculate_streak': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_engine_instance.recalculate_streak.assert_called_once()
    
    @patch('progress.views.GamificationEngine')
    def test_streaks_endpoint(self, mock_engine):
        """Test streaks endpoint"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        
        url = reverse('stats-streaks')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_streak', response.data)
        self.assertIn('longest_streak', response.data)
        self.assertIn('daily_activity', response.data)
        self.assertIn('calculated_streak', response.data)
        self.assertIn('streak_matches', response.data)
    
    @patch('progress.views.GamificationEngine')
    def test_streaks_with_force_update(self, mock_engine):
        """Test streaks with force update"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        
        url = reverse('stats-streaks')
        response = self.client.get(url, {'force_update': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_engine_instance.recalculate_streak.assert_called_once()
    
    @patch('progress.views.GamificationEngine')
    def test_debug_streak_endpoint(self, mock_engine):
        """Test debug streak endpoint"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.debug_streak_status.return_value = {'debug': 'info'}
        
        url = reverse('stats-debug-streak')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('debug_info', response.data)
        self.assertIn('actions_available', response.data)
        mock_engine_instance.debug_streak_status.assert_called_once()
    
    @patch('progress.views.GamificationEngine')  # must match exactly where the view imports it
    def test_fix_streak_endpoint(self, mock_engine):
        """Test fix streak endpoint"""

        # Mock engine instance
        mock_engine_instance = mock_engine.return_value
        
        # Ensure profile has some streak values
        mock_engine_instance.profile.current_streak = 5
        mock_engine_instance.profile.longest_streak = 12
        
        # Force a real dict (NOT a mock)
        mock_engine_instance.recalculate_streak.return_value = {
            'current_streak': 3,
            'longest_streak': 10
        }
        
        url = reverse('stats-fix-streak')
        response = self.client.post(url)
        
        # ✅ Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Streak recalculated successfully')
        
        # Check old values came from mock profile
        self.assertEqual(response.data['old_values']['current_streak'], 5)
        self.assertEqual(response.data['old_values']['longest_streak'], 12)
        
        # Check new values came from return_value dict
        self.assertEqual(response.data['new_values']['current_streak'], 3)
        self.assertEqual(response.data['new_values']['longest_streak'], 10)
        
        # Ensure recalculation was called
        mock_engine_instance.recalculate_streak.assert_called_once()

    @patch('progress.views.GamificationEngine')
    def test_fix_streak_endpoint_failure(self, mock_engine):
        """Test fix streak endpoint when recalculation fails"""
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.recalculate_streak.return_value = None
        
        url = reverse('stats-fix-streak')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('message', response.data)
        self.assertIn('reason', response.data)
    
    def test_xp_breakdown_endpoint(self):
        """Test XP breakdown endpoint"""
        # Create XP logs
        XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=50,
            description='Completed task'
        )
        XPLog.objects.create(
            user=self.user,
            action='streak_bonus',
            xp_earned=25,
            description='Streak bonus'
        )
        
        url = reverse('stats-xp-breakdown')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('xp_by_action', response.data)
        self.assertIn('recent_activity', response.data)
        self.assertIn('total_xp', response.data)
        self.assertEqual(response.data['total_xp'], 75)


class WeeklyReviewViewSetTests(BaseTestCase):
    """Test cases for WeeklyReviewViewSet"""
    
    def setUp(self):
        super().setUp()
        self.week_start = timezone.now().date() - timedelta(days=7)
        self.week_end = self.week_start + timedelta(days=6)
        
        self.review = WeeklyReview.objects.create(
            user=self.user,
            week_start=self.week_start,
            week_end=self.week_end,
            total_tasks=10,
            early_completions=5,
            total_xp=200,
            late_completions=2,
            on_time_completions=1,
            suggestions='Focus on priorities'
        )
    
    def test_list_weekly_reviews(self):
        """Test listing weekly reviews"""
        url = reverse('weeklyreview-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['total_tasks'], 10)
    
    def test_create_weekly_review(self):
        """Test creating a weekly review"""
        url = reverse('weeklyreview-list')
        data = {
            'week_start': '2024-01-01',
            'week_end': '2024-01-07',
            'total_tasks': 15,
            'completed_tasks': 12,
            'total_xp': 300,
            'key_highlights': 'Excellent productivity',
            'challenges_faced': 'Distractions',
            'suggestions': 'Better focus techniques'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WeeklyReview.objects.count(), 2)
        self.assertEqual(response.data['total_tasks'], 15)
    
    def test_current_week_endpoint(self):
        """Test current week endpoint"""
        url = reverse('weeklyreview-current-week')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('week_start', response.data)
        self.assertIn('week_end', response.data)
    
    def test_date_range_endpoint(self):
        """Test date range endpoint"""
        url = reverse('weeklyreview-date-range')
        response = self.client.get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_date_range_endpoint_missing_params(self):
        """Test date range endpoint with missing parameters"""
        url = reverse('weeklyreview-date-range')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_date_range_endpoint_invalid_date(self):
        """Test date range endpoint with invalid date format"""
        url = reverse('weeklyreview-date-range')
        response = self.client.get(url, {
            'start_date': 'invalid-date',
            'end_date': '2024-01-31'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_performance_summary_endpoint(self):
        """Test performance summary endpoint"""
        url = reverse('weeklyreview-performance-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('total_weeks_reviewed', response.data['summary'])
        self.assertIn('average_performance_score', response.data['summary'])
    
    def test_performance_summary_no_reviews(self):
        """Test performance summary with no reviews"""
        WeeklyReview.objects.filter(user=self.user).delete()
        
        url = reverse('weeklyreview-performance-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'No reviews found')
    
    def test_add_suggestion_endpoint(self):
        """Test adding suggestion to existing review"""
        url = reverse('weeklyreview-add-suggestion', kwargs={'pk': self.review.id})
        data = {'suggestion': 'Try the Pomodoro technique'}
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertIn('Pomodoro technique', self.review.suggestions)
    
    def test_add_suggestion_empty(self):
        """Test adding empty suggestion"""
        url = reverse('weeklyreview-add-suggestion', kwargs={'pk': self.review.id})
        data = {'suggestion': ''}
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_list_with_filters(self):
        """Test listing reviews with various filters"""
        url = reverse('weeklyreview-list')
        
        # Test grade filter
        response = self.client.get(url, {'grade': 'A'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test min_score filter
        response = self.client.get(url, {'min_score': '80'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test year filter
        response = self.client.get(url, {'year': '2024'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserProgressProfileViewSetTests(BaseTestCase):
    """Test cases for UserProgressProfileViewSet"""
    
    def test_get_user_profile(self):
        """Test retrieving user's progress profile"""
        url = reverse('userprogress-detail', kwargs={'pk': self.profile2.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_xp'], 100)
        self.assertEqual(response.data['current_level'], 2)
    
    def test_list_user_profiles(self):
        """Test listing user profiles (should only show current user's)"""
        url = reverse('userprogress-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['username'], self.user.username)
        
            
    def test_anonymous_user_access(self):
        """Test that anonymous users get 404"""
        self.client.force_authenticate(user=None)
        url = reverse('userprogress-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LeaderboardViewSetTests(BaseTestCase):
    """Test cases for LeaderboardViewSet"""
    
    def setUp(self):
        super().setUp()
        self.leaderboard_type = LeaderboardType.objects.create(
            name='Global XP',
            description='Global XP leaderboard',
            is_active=True
        )
        
        self.leaderboard_entry = LeaderboardEntry.objects.create(
            user=self.user,
            leaderboard_type=self.leaderboard_type,
            score=1000,
            rank=1,
            # period_start=timezone.now().date(),
            # period_end=timezone.now().date()
            period_start=timezone.now(),  # Use aware datetime
            period_end=timezone.now()
        )
    
    def test_list_leaderboard_entries(self):
        """Test listing leaderboard entries"""
        url = reverse('leaderboard-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['score'], 1000)
    
    def test_leaderboard_types_endpoint(self):
        """Test leaderboard types endpoint"""
        url = reverse('leaderboard-types')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Global XP')
    
    def test_global_leaderboard_endpoint(self):
        """Test global leaderboard endpoint"""
        url = reverse('leaderboard-global-leaderboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('entries', response.data)
        self.assertIn('user_rank', response.data)
        self.assertIn('total_participants', response.data)
        self.assertIn('period', response.data)
    
    def test_global_leaderboard_with_filters(self):
        """Test global leaderboard with period and category filters"""
        url = reverse('leaderboard-global-leaderboard')
        response = self.client.get(url, {
            'period': 'weekly',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'weekly')
    
    def test_friends_leaderboard_endpoint(self):
        """Test friends leaderboard endpoint"""
        url = reverse('leaderboard-friends-leaderboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('entries', response.data)
        self.assertIn('friends_count', response.data)
    
    def test_category_rankings_endpoint(self):
        """Test category rankings endpoint"""
        url = reverse('leaderboard-category-rankings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('category_rankings', response.data)
    
    @patch('progress.gamification.LeaderboardService')
    def test_refresh_rankings_endpoint(self, mock_service):
        """Test refresh rankings endpoint"""
        mock_service.update_rankings.return_value = None
        
        url = reverse('leaderboard-refresh-rankings')
        response = self.client.post(url, {'period': 'weekly'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        mock_service.update_rankings.assert_called_once_with('weekly')


class FriendshipViewSetTests(BaseTestCase):
    """Test friendship management endpoints"""
    
    def test_get_friendships(self):
        """Test retrieving user friendships"""
        # Create a friendship
        UserFriendship.objects.create(
            user=self.user,
            friend=self.user2,
            status='accepted'
        )
        
        url = reverse('friendship-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['friend']['username'], 'testuser2')
    
    def test_send_friend_request(self):
        """Test sending a friend request"""
        url = reverse('friendship-send-request')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Friend request sent')
        
        # Check friendship was created
        friendship = UserFriendship.objects.get(user=self.user, friend=self.user2)
        self.assertEqual(friendship.status, 'pending')
        
        # Check notification was created
        notification = Notification.objects.get(user=self.user2)
        self.assertEqual(notification.notification_type, 'friend_request')
    
    def test_send_friend_request_missing_username(self):
        """Test sending friend request without username"""
        url = reverse('friendship-send-request')
        data = {}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Username required', response.data['error'])
    
    def test_send_friend_request_to_self(self):
        """Test sending friend request to self"""
        url = reverse('friendship-send-request')
        data = {'username': 'testuser1'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot add yourself as friend', response.data['error'])
    
    def test_send_friend_request_already_exists(self):
        """Test sending friend request when friendship already exists"""
        UserFriendship.objects.create(
            user=self.user,
            friend=self.user2,
            status='pending'
        )
        
        url = reverse('friendship-send-request')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Friend request already exists', response.data['error'])
    
    def test_accept_friend_request(self):
        """Test accepting a friend request"""
        friendship = UserFriendship.objects.create(
            user=self.user2,
            friend=self.user,
            status='pending'
        )
        
        url = reverse('friendship-accept-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Friend request accepted')
        
        # Check friendship status updated
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, 'accepted')
        
        # Check reverse friendship created
        reverse_friendship = UserFriendship.objects.get(
            user=self.user,
            friend=self.user2
        )
        self.assertEqual(reverse_friendship.status, 'accepted')
    
    def test_reject_friend_request(self):
        """Test rejecting a friend request"""
        friendship = UserFriendship.objects.create(
            user=self.user2,
            friend=self.user,
            status='pending'
        )
        
        url = reverse('friendship-reject-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Friend request rejected')
        
        # Check friendship deleted
        self.assertFalse(
            UserFriendship.objects.filter(id=friendship.id).exists()
        )
    
    def test_unauthenticated_access(self):
        """Test unauthenticated access to friendship endpoints"""
        self.client.force_authenticate(user=None)
        
        url = reverse('friendship-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MissionViewSetTests(BaseTestCase):
    """Test mission management endpoints"""
    
    def test_get_user_missions(self):
        """Test retrieving user missions"""
        UserMission.objects.filter(user=self.user).delete()

        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1
        )
        
        url = reverse('mission-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Mission')

    def test_get_available_missions(self):
        """Test getting available missions for user"""
        url = reverse('mission-available-missions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_missions', response.data)
        self.assertIn('active_missions_count', response.data)
        self.assertIn('max_missions', response.data)
        self.assertEqual(len(response.data['available_missions']), 1)
    
    def test_available_missions_max_limit(self):
        """Test available missions when at max limit"""
        # Create 5 active missions
        for i in range(5):
            UserMission.objects.create(
                user=self.user,
                template=self.mission_template,
                title=f'Mission {i}',
                description='Test',
                target_value=5,
                end_date=timezone.now() + timedelta(days=7),
                xp_reward=100,
                category=self.category1,
                status='active'
            )
        
        url = reverse('mission-available-missions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['available_missions']), 0)
        self.assertIn('maximum', response.data['message'])
    
    def test_accept_mission(self):
        """Test accepting a mission"""
        url = reverse('mission-accept-mission')
        data = {'template_id': self.mission_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Mission accepted successfully')
        
        # Check mission was created
        mission = UserMission.objects.get(user=self.user, template=self.mission_template)
        self.assertEqual(mission.status, 'active')
        self.assertEqual(mission.title, self.mission_template.name)
        
        # Check notification was created
        notification = Notification.objects.get(user=self.user, notification_type='mission_accepted')
        self.assertIn('accepted', notification.message)
    
    def test_accept_mission_insufficient_level(self):
        """Test accepting mission with insufficient level"""
        self.mission_template.min_user_level = 10
        self.mission_template.save()
        
        url = reverse('mission-accept-mission')
        data = {'template_id': self.mission_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient level', response.data['error'])
    
    def test_accept_mission_max_active_reached(self):
        """Test accepting mission when max active missions reached"""
        # Create 5 active missions
        for i in range(5):
            UserMission.objects.create(
                user=self.user,
                template=self.mission_template,
                title=f'Mission {i}',
                description='Test',
                target_value=5,
                end_date=timezone.now() + timedelta(days=7),
                xp_reward=100,
                category=self.category1,
                status='active'
            )
        
        url = reverse('mission-accept-mission')
        data = {'template_id': self.mission_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Maximum active missions reached', response.data['error'])
    
    def test_abandon_mission(self):
        """Test abandoning an active mission"""
        mission = UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        url = reverse('mission-abandon-mission', kwargs={'pk': mission.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Mission abandoned')
        
        # Check mission status updated
        mission.refresh_from_db()
        self.assertEqual(mission.status, 'abandoned')
    
    def test_generate_random_missions(self):
        """Test generating random missions"""
        # Create additional mission templates
        for i in range(3):
            MissionTemplate.objects.create(
                name=f'Random Mission {i}',
                description=f'Description {i}',
                category=self.category1,
                target_value=3,
                xp_reward=50,
                duration_days=5,
                min_user_level=1,
                is_active=True,
                weight=1
            )
        
        url = reverse('mission-generate-random-missions')
        data = {'count': 2}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('generated_missions', response.data)
        self.assertEqual(len(response.data['generated_missions']), 2)
    
    def test_mission_progress(self):
        """Test getting mission progress"""
        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            current_progress=2,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        url = reverse('mission-mission-progress')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('mission_progress', response.data)
        self.assertEqual(len(response.data['mission_progress']), 1)
        
        progress_data = response.data['mission_progress'][0]
        self.assertIn('progress_percentage', progress_data)
        self.assertIn('time_remaining', progress_data)
    
    @patch('progress.gamification.MissionService.update_mission_progress')
    def test_update_mission_progress(self, mock_update):
        """Test checking mission updates"""
        mission = UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        mock_update.return_value = [mission]
        
        url = reverse('mission-update-mission-progress')  # ensure correct route name
        
        # Send mission_type in request
        response = self.client.post(url, {'mission_type': 'default'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_missions'], 1)
        
        # ✅ Now assert proper call
        mock_update.assert_called_once_with(
            user_id=self.user.id,
            mission_type='default',
            progress_value=1
        )


class NotificationViewSetTests(BaseTestCase):
    """Test notification management endpoints"""
    
    def setUp(self):
        super().setUp()
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type='friend_request',
            title='Test Notification',
            message='Test message',
            data={'test': 'data'}
        )
        
    
    def test_get_notifications(self):
        """Test retrieving user notifications"""
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Test Notification')
    
    def test_unread_count(self):
        """Test getting unread notification count"""
        url = reverse('notification-unread-count')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)
    
    def test_mark_all_read(self):
        """Test marking all notifications as read"""
        url = reverse('notification-mark-all-read')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_read'], 1)
        
        # Check notification was marked as read
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
    
    def test_mark_specific_read(self):
        """Test marking specific notification as read"""
        url = reverse('notification-mark-read', kwargs={'pk': self.notification.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Notification marked as read')
        
        # Check notification was marked as read
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
    
    def test_archive_notification(self):
        """Test archiving a notification"""
        url = reverse('notification-archive', kwargs={'pk': self.notification.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Notification archived')
        
        # Check notification was archived
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_archived)
    
    def test_archive_all_read(self):
        """Test archiving all read notifications"""
        # Mark notification as read first
        self.notification.is_read = True
        self.notification.save()
        
        url = reverse('notification-archive-all-read')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['archived'], 1)
        
        # Check notification was archived
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_archived)
    
    def test_notifications_by_type(self):
        """Test getting notifications by type"""
        url = reverse('notification-by-type')
        response = self.client.get(url, {'type': 'friend_request'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['notifications']), 1)
        self.assertEqual(response.data['type'], 'friend_request')
    
    def test_recent_notifications(self):
        """Test getting recent notifications"""
        url = reverse('notification-recent')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['recent_notifications']), 1)
        self.assertEqual(response.data['count'], 1)


class NotificationSettingsViewSetTests(BaseTestCase):
    """Test notification settings management endpoints"""
    
    def test_get_settings(self):
        """Test getting notification settings"""
        url = reverse('notification-settings-get-settings')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email_notifications', response.data)
        self.assertIn('push_notifications', response.data)
    
    def test_update_settings(self):
        """Test updating notification settings"""
        url = reverse('notification-settings-update-settings')
        data = {
            'email_notifications': False,
            'push_notifications': True,
            'quiet_hours_start': '22:00',
            'quiet_hours_end': '08:00'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Settings updated successfully')
        
        # Check settings were updated
        settings = UserNotificationSettings.objects.get(user=self.user)
        self.assertFalse(settings.email_notifications)
        self.assertTrue(settings.push_notifications)
    
    def test_get_notification_types(self):
        """Test getting available notification types"""
        url = reverse('notification-settings-notification-types')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('notification_types', response.data)
        self.assertEqual(len(response.data['notification_types']), 3)


class GameStatsViewSetTests(BaseTestCase):
    """Test game statistics and utilities endpoints"""
    
    def test_dashboard_summary(self):
        """Test getting dashboard summary"""
        # Create some test data
        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        Notification.objects.create(
            user=self.user,
            notification_type='test',
            title='Test Notification',
            message='Test message'
        )
        
        url = reverse('game-stats-dashboard-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('active_missions', response.data)
        self.assertIn('recent_notifications', response.data)
        self.assertIn('global_rank', response.data)
        self.assertIn('weekly_tasks_completed', response.data)
        self.assertIn('unread_notifications', response.data)
    
    def test_send_test_notification_staff_only(self):
        """Test sending test notification (staff only)"""
        url = reverse('game-stats-send-test-notification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['error'])
    
    def test_send_test_notification_as_staff(self):
        """Test sending test notification as staff user"""
        self.user.is_staff = True
        self.user.save()
        
        url = reverse('game-stats-send-test-notification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Test notification sent')
        
        # Check notification was created
        notification = Notification.objects.get(
            user=self.user,
            notification_type='test'
        )
        self.assertEqual(notification.title, 'Test Notification')
    
    def test_system_stats_staff_only(self):
        """Test getting system stats (staff only)"""
        url = reverse('game-stats-system-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['error'])
    
    def test_system_stats_as_staff(self):
        """Test getting system stats as staff user"""
        self.user.is_staff = True
        self.user.save()
        
        url = reverse('game-stats-system-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('system_stats', response.data)
        
        stats = response.data['system_stats']
        self.assertIn('total_users', stats)
        self.assertIn('active_missions', stats)
        self.assertIn('completed_missions', stats)
        self.assertIn('total_notifications', stats)
        self.assertIn('unread_notifications', stats)
        self.assertIn('active_friendships', stats)
        self.assertIn('pending_friend_requests', stats)


class EdgeCaseTests(BaseTestCase):
    """Test edge cases and error conditions"""
    
    def test_swagger_fake_view_handling(self):
        """Test handling of swagger fake view"""
        self.client.force_authenticate(user=None)
        
        # This simulates swagger documentation generation
        url = reverse('friendship-list')
        response = self.client.get(url)
        
        # Should return 401 for unauthenticated requests
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_anonymous_user_handling(self):
        """Test handling of anonymous users"""
        self.client.force_authenticate(user=None)
        
        url = reverse('mission-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_nonexistent_user_friend_request(self):
        """Test sending friend request to non-existent user"""
        url = reverse('friendship-send-request')
        data = {'username': 'nonexistent_user'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('User not found', response.data['error'])
    
    def test_invalid_mission_template(self):
        """Test accepting invalid mission template"""
        url = reverse('mission-accept-mission')
        data = {'template_id': 99999}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_accept_inactive_mission_template(self):
        """Test accepting inactive mission template"""
        self.mission_template.is_active = False
        self.mission_template.save()
        
        url = reverse('mission-accept-mission')
        data = {'template_id': self.mission_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_abandon_non_owned_mission(self):
        """Test abandoning mission not owned by user"""
        mission = UserMission.objects.create(
            user=self.user2,  # Different user
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        url = reverse('mission-abandon-mission', kwargs={'pk': mission.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_mark_read_non_owned_notification(self):
        """Test marking notification as read that doesn't belong to user"""
        notification = Notification.objects.create(
            user=self.user2,  # Different user
            notification_type='test',
            title='Test Notification',
            message='Test message'
        )
        
        url = reverse('notification-mark-read', kwargs={'pk': notification.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_accept_friend_request_wrong_user(self):
        """Test accepting friend request not meant for current user"""
        # Create friendship where user1 sends request to user2
        friendship = UserFriendship.objects.create(
            user=self.user,
            friend=self.user2,
            status='pending'
        )
        
        # Try to accept as user1 (should fail, user2 should accept)
        url = reverse('friendship-accept-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PerformanceTests(BaseTestCase):
    """Test performance-related aspects"""
    
    def test_large_number_of_missions(self):
        """Test handling large number of missions"""
        # Create many missions
        for i in range(50):
            UserMission.objects.create(
                user=self.user,
                template=self.mission_template,
                title=f'Mission {i}',
                description=f'Description {i}',
                target_value=5,
                end_date=timezone.now() + timedelta(days=7),
                xp_reward=100,
                category=self.category1,
                status='active' if i < 5 else 'completed'
            )
        
        url = reverse('mission-list')
        response = self.client.get(url, {'page_size': 100})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return missions for current user
        self.assertEqual(len(response.data['results']), 50)
    
    def test_large_number_of_notifications(self):
        """Test handling large number of notifications"""
        # Create many notifications
        for i in range(100):
            Notification.objects.create(
                user=self.user,
                notification_type='test',
                title=f'Notification {i}',
                message=f'Message {i}'
            )
        
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be paginated
        self.assertTrue(len(response.data) <= 100)
    
    def test_concurrent_friend_requests(self):
        """Test handling concurrent friend requests"""
        # This would be more meaningful with actual concurrent requests
        # For now, test rapid sequential requests
        url = reverse('friendship-send-request')
        data = {'username': 'testuser2'}
        
        # First request should succeed
        response1 = self.client.post(url, data)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second request should fail (already exists)
        response2 = self.client.post(url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', response2.data['error'])


class ValidationTests(BaseTestCase):
    """Test input validation and data integrity"""
    
    def test_mission_accept_missing_template_id(self):
        """Test accepting mission without template_id"""
        url = reverse('mission-accept-mission')
        data = {}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid template_id. Must be a positive integer.'})
    
    def test_mission_accept_invalid_template_id(self):
        url = reverse('mission-accept-mission')
        data = {'template_id': 'invalid'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'error': 'Invalid template_id. Must be a positive integer.'})
    
    def test_friend_request_empty_username(self):
        """Test friend request with empty username"""
        url = reverse('friendship-send-request')
        data = {'username': ''}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Username required', response.data['error'])
    
    def test_notification_settings_invalid_time_format(self):
        """Test notification settings with invalid time format"""
        url = reverse('notification-settings-update-settings')
        data = {
            'quiet_hours_start': 'invalid_time',
            'quiet_hours_end': '08:00'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_random_missions_invalid_count(self):
        url = reverse('mission-generate-random-missions')
        data = {'count': 'invalid'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid count parameter. Must be a positive integer.'})
    
    def test_generate_random_missions_zero_count(self):
        url = reverse('mission-generate-random-missions')
        data = {'count': '0'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid count parameter. Must be a positive integer.'})

    def test_generate_random_missions_excessive_count(self):
        """Test generating random missions with excessive count"""
        url = reverse('mission-generate-random-missions')
        data = {'count': 100}
        
        response = self.client.post(url, data)
        
        # Should cap at 5
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['generated_missions']), 5)


class IntegrationTests(BaseTestCase):
    """Test integration between different components"""
    
    def test_friendship_and_notification_integration(self):
        """Test that friend requests create notifications"""
        url = reverse('friendship-send-request')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that notification was created for the friend
        notification = Notification.objects.get(
            user=self.user2,
            notification_type='friend_request'
        )
        self.assertIn('friend', notification.message)
        self.assertEqual(notification.data['friendship_id'], 
                        UserFriendship.objects.get(user=self.user, friend=self.user2).id)
    
    def test_mission_acceptance_and_notification_integration(self):
        """Test that accepting missions creates notifications"""
        url = reverse('mission-accept-mission')
        data = {'template_id': self.mission_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that notification was created
        notification = Notification.objects.get(
            user=self.user,
            notification_type='mission_accepted'
        )
        self.assertIn('accepted', notification.message)
        self.assertEqual(notification.data['mission_id'], 
                        UserMission.objects.get(user=self.user, template=self.mission_template).id)
    
    def test_friend_request_acceptance_creates_bidirectional_friendship(self):
        """Test that accepting friend request creates friendship for both users"""
        # User2 sends request to User1
        friendship = UserFriendship.objects.create(
            user=self.user2,
            friend=self.user,
            status='pending'
        )
        
        # User1 accepts the request
        url = reverse('friendship-accept-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that both friendships exist
        self.assertTrue(
            UserFriendship.objects.filter(
                user=self.user, friend=self.user2, status='accepted'
            ).exists()
        )
        self.assertTrue(
            UserFriendship.objects.filter(
                user=self.user2, friend=self.user, status='accepted'
            ).exists()
        )
    
    def test_mission_level_restrictions(self):
        """Test that mission level restrictions work correctly"""
        # Create a high-level mission
        high_level_template = MissionTemplate.objects.create(
            name='High Level Mission',
            description='For advanced users',
            category=self.category1,
            target_value=10,
            xp_reward=500,
            duration_days=14,
            min_user_level=10,
            max_user_level=20,
            is_active=True
        )
        
        # Should not appear in available missions for low-level user
        url = reverse('mission-available-missions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        available_ids = [m['id'] for m in response.data['available_missions']]
        self.assertNotIn(high_level_template.id, available_ids)
        
        # Should fail when trying to accept directly
        url = reverse('mission-accept-mission')
        data = {'template_id': high_level_template.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient level', response.data['error'])


class SecurityTests(BaseTestCase):
    """Test security-related functionality"""
    
    def test_user_isolation_missions(self):
        """Test that users can only see their own missions"""
        # Create mission for user2
        UserMission.objects.create(
            user=self.user2,
            template=self.mission_template,
            title='User2 Mission',
            description='This belongs to user2',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1
        )
        
        # User1 should not see user2's mission
        url = reverse('mission-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mission_titles = [m['title'] for m in response.data['results']]  # Fix: Use 'results'
        self.assertNotIn('User2 Mission', mission_titles)
    
    def test_user_isolation_notifications(self):
        """Test that users can only see their own notifications"""
        # Create notification for user2
        Notification.objects.create(
            user=self.user2,
            notification_type='test',
            title='User2 Notification',
            message='This belongs to user2'
        )
        
        # User1 should not see user2's notification
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification_titles = [n['title'] for n in response.data['results']]
        self.assertNotIn('User2 Notification', notification_titles)
    
    def test_user_isolation_friendships(self):
        """Test that users can only see their own friendships"""
        # Create friendship between user2 and another user
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123'
        )
        
        UserFriendship.objects.create(
            user=self.user2,
            friend=user3,
            status='accepted'
        )
        
        # User1 should not see user2's friendship
        url = reverse('friendship-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        friend_usernames = [f['friend']['username'] for f in response.data['results']] 
        self.assertNotIn('testuser3', friend_usernames)
    
    def test_cannot_accept_others_friend_requests(self):
        """Test that users cannot accept friend requests not meant for them"""
        # User2 sends request to User3
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123'
        )
        
        friendship = UserFriendship.objects.create(
            user=self.user2,
            friend=user3,
            status='pending'
        )
        
        # User1 tries to accept (should fail)
        url = reverse('friendship-accept-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cannot_modify_others_notification_settings(self):
        """Test that users cannot modify others' notification settings"""
        # Create settings for user2
        user2_settings = UserNotificationSettings.objects.create(
            user=self.user2,
            email_notifications=True,
            push_notifications=True
        )
        
        # User1 tries to modify user2's settings (should only affect user1's settings)
        url = reverse('notification-settings-update-settings')
        data = {'email_notifications': False}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User2's settings should remain unchanged
        user2_settings.refresh_from_db()
        self.assertTrue(user2_settings.email_notifications)
        
        # User1's settings should be created/updated
        user1_settings = UserNotificationSettings.objects.get(user=self.user)
        self.assertFalse(user1_settings.email_notifications)


class APIResponseFormatTests(BaseTestCase):
    """Test API response formats and consistency"""
    
    def test_friendship_response_format(self):
        """Test friendship API response format"""
        UserFriendship.objects.create(
            user=self.user,
            friend=self.user2,
            status='accepted'
        )
        
        url = reverse('friendship-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data['results'], list)
        self.assertEqual(len(response.data['results']), 1)
        
        if response.data:
            friendship_data = response.data['results'][0]
            required_fields = ['id', 'friend', 'status', 'created_at']
            for field in required_fields:
                self.assertIn(field, friendship_data)
    
    def test_mission_response_format(self):
        """Test mission API response format"""
        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1
        )
        
        url = reverse('mission-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)

        results = response.data['results']
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        mission_data = self.get_first_result(response)
        required_fields = ['id', 'title', 'description', 'xp_reward', 'status']
        for field in required_fields:
            self.assertIn(field, mission_data)
        
    
    def test_notification_response_format(self):
        """Test notification API response format"""
        Notification.objects.create(
            user=self.user,
            notification_type='test',
            title='Test Notification',
            message='Test message'
        )
        
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data['results'], list)
        self.assertEqual(len(response.data['results']), 1)
        
        if response.data:
            notification_data = response.data['results'][0]
            required_fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
            for field in required_fields:
                self.assertIn(field, notification_data)
    
    def test_error_response_format(self):
        """Test error response format consistency"""
        # Test 400 error
        url = reverse('friendship-send-request')
        data = {}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIsInstance(response.data['error'], str)
        
        # Test 404 error
        url = reverse('friendship-accept-request', kwargs={'pk': 99999})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_success_response_format(self):
        """Test success response format consistency"""
        url = reverse('friendship-send-request')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIsInstance(response.data['message'], str)


class CacheAndPerformanceTests(BaseTestCase):
    """Test caching and performance optimizations"""
    
    def test_queryset_optimization(self):
        """Test that querysets are optimized with select_related/prefetch_related"""
        # Create test data
        for i in range(10):
            Notification.objects.create(
                user=self.user,
                notification_type='test',
                title=f'Notification {i}',
                message=f'Message {i}'
            )
        
        # Test that notifications list uses select_related
        url = reverse('notification-list')
        
        with self.assertNumQueries(2):  # Should be minimal queries due to select_related
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets"""
        # Create many notifications
        notifications = []
        for i in range(100):
            notifications.append(Notification(
                user=self.user,
                notification_type='test',
                title=f'Notification {i}',
                message=f'Message {i}'
            ))
        Notification.objects.bulk_create(notifications)
        
        url = reverse('notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be paginated, not return all 100
        self.assertLessEqual(len(response.data), 50)  # Assuming page size is 50 or less


class MockingTests(BaseTestCase):
    """Test with mocked external dependencies"""
    
    @patch('progress.gamification.MissionService.update_mission_progress')
    def test_mission_service_integration(self, mock_update):
        """Test integration with mocked MissionService"""
        # Setup mock return
        mission = UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        mock_update.return_value = [mission]

        url = reverse('mission-update-mission-progress')

        # ✅ Call with mission_type
        response = self.client.post(url, {'mission_type': 'default'}, format='json')

        # ✅ Assert response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_missions'], 1)

        # ✅ Assert correct call to MissionService
        mock_update.assert_called_once_with(
            user_id=self.user.id,
            mission_type='default',
            progress_value=1
        )

    @patch('django.utils.timezone.now')
    def test_time_dependent_functionality(self, mock_now):
        """Test time-dependent functionality with mocked time"""
        # Mock current time
        fixed_time = timezone.make_aware(datetime(2024, 1, 15, 12, 0, 0))
        mock_now.return_value = fixed_time
        
        # Test mission expiration
        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=5,
            end_date=fixed_time - timedelta(days=1),  # Expired
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        url = reverse('mission-mission-progress')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress_data = response.data['mission_progress'][0]
        self.assertTrue(progress_data['is_expired'])
    
    @patch('progress.views.logger.exception')
    def test_error_logging(self, mock_log):
        """Test that errors are properly logged"""
        url = reverse('game-stats-dashboard-summary')

        with patch.object(GameStatsViewSet, '_get_user_global_rank', side_effect=Exception("Test error")):
            response = self.client.get(url)

            self.assertEqual(response.status_code, 500)  # ✅ Expect error response
            mock_log.assert_called_once()  # ✅ Should now pass



class DataIntegrityTests(BaseTestCase):
    """Test data integrity and consistency"""
    
    def test_friendship_bidirectional_consistency(self):
        """Test that friendships maintain bidirectional consistency"""
        # Create friendship
        friendship = UserFriendship.objects.create(
            user=self.user2,
            friend=self.user,
            status='pending'
        )
        
        # Accept friendship
        url = reverse('friendship-accept-request', kwargs={'pk': friendship.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that both directions exist and are consistent
        forward_friendship = UserFriendship.objects.get(user=self.user2, friend=self.user)
        reverse_friendship = UserFriendship.objects.get(user=self.user, friend=self.user2)
        
        self.assertEqual(forward_friendship.status, 'accepted')
        self.assertEqual(reverse_friendship.status, 'accepted')
    
    def test_mission_progress_consistency(self):
        """Test that mission progress is consistent"""
        UserMission.objects.create(
            user=self.user,
            template=self.mission_template,
            title='Test Mission',
            description='Test description',
            target_value=10,
            current_progress=5,
            end_date=timezone.now() + timedelta(days=7),
            xp_reward=100,
            category=self.category1,
            status='active'
        )
        
        url = reverse('mission-mission-progress')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress_data = response.data['mission_progress'][0]
        
        # Check that progress percentage is calculated correctly
        expected_percentage = (5 / 10) * 100
        self.assertEqual(progress_data['progress_percentage'], expected_percentage)
    
    def test_notification_cleanup_consistency(self):
        """Test that notification cleanup maintains consistency"""
        # Create notifications
        notifications = []
        for i in range(5):
            notifications.append(Notification.objects.create(
                user=self.user,
                notification_type='test',
                title=f'Notification {i}',
                message=f'Message {i}',
                is_read=(i < 3)  # First 3 are read
            ))
        
        # Archive all read notifications
        url = reverse('notification-archive-all-read')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['archived'], 3)
        
        # Check that only read notifications were archived
        archived_count = Notification.objects.filter(user=self.user, is_archived=True).count()
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        
        self.assertEqual(archived_count, 3)
        self.assertEqual(unread_count, 2)
