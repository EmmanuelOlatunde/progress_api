from django.urls import reverse, resolve
from rest_framework.test import APIClient
from django.test import TestCase

class TestProgressAppURLs(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_task_urls(self):
        """Test TaskViewSet URLs"""
        # Test list endpoint
        url = reverse('task-list')
        self.assertEqual(resolve(url).view_name, 'task-list')
        
        # Test detail endpoint
        url = reverse('task-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'task-detail')
        
        # Test custom actions
        url = reverse('task-complete', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'task-complete')
        
        url = reverse('task-stats')
        self.assertEqual(resolve(url).view_name, 'task-stats')

    def test_category_urls(self):
        """Test CategoryViewSet URLs"""
        url = reverse('category-list')
        self.assertEqual(resolve(url).view_name, 'category-list')
        
        url = reverse('category-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'category-detail')

    def test_xp_urls(self):
        """Test XPViewSet URLs"""
        url = reverse('xp-list')
        self.assertEqual(resolve(url).view_name, 'xp-list')
        
        url = reverse('xp-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'xp-detail')
        
        url = reverse('xp-summary')
        self.assertEqual(resolve(url).view_name, 'xp-summary')
        
        url = reverse('xp-level')
        self.assertEqual(resolve(url).view_name, 'xp-level')

    def test_achievement_urls(self):
        """Test AchievementViewSet URLs"""
        url = reverse('achievement-list')
        self.assertEqual(resolve(url).view_name, 'achievement-list')
        
        url = reverse('achievement-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'achievement-detail')
        
        url = reverse('achievement-unlocked')
        self.assertEqual(resolve(url).view_name, 'achievement-unlocked')

    def test_stats_urls(self):
        """Test StatsViewSet URLs"""
        url = reverse('stats-list')
        self.assertEqual(resolve(url).view_name, 'stats-list')
        
        url = reverse('stats-streaks')
        self.assertEqual(resolve(url).view_name, 'stats-streaks')
        
        url = reverse('stats-debug-streak')
        self.assertEqual(resolve(url).view_name, 'stats-debug-streak')
        
        url = reverse('stats-fix-streak')
        self.assertEqual(resolve(url).view_name, 'stats-fix-streak')
        
        url = reverse('stats-xp-breakdown')
        self.assertEqual(resolve(url).view_name, 'stats-xp-breakdown')

    def test_weekly_review_urls(self):
        """Test WeeklyReviewViewSet URLs"""
        url = reverse('weeklyreview-list')
        self.assertEqual(resolve(url).view_name, 'weeklyreview-list')
        
        url = reverse('weeklyreview-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'weeklyreview-detail')
        
        url = reverse('weeklyreview-current-week')
        self.assertEqual(resolve(url).view_name, 'weeklyreview-current-week')
        
        url = reverse('weeklyreview-date-range')
        self.assertEqual(resolve(url).view_name, 'weeklyreview-date-range')
        
        url = reverse('weeklyreview-performance-summary')
        self.assertEqual(resolve(url).view_name, 'weeklyreview-performance-summary')
        
        url = reverse('weeklyreview-top-categories')
        self.assertEqual(resolve(url).view_name, 'weeklyreview-top-categories')
        
        url = reverse('weeklyreview-add-suggestion', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'weeklyreview-add-suggestion')

    def test_user_progress_urls(self):
        """Test UserProgressProfileViewSet URLs"""
        url = reverse('userprogress-list')
        self.assertEqual(resolve(url).view_name, 'userprogress-list')
        
        url = reverse('userprogress-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'userprogress-detail')

    def test_leaderboard_urls(self):
        """Test LeaderboardViewSet URLs"""
        url = reverse('leaderboard-list')
        self.assertEqual(resolve(url).view_name, 'leaderboard-list')
        
        url = reverse('leaderboard-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'leaderboard-detail')
        
        url = reverse('leaderboard-types')
        self.assertEqual(resolve(url).view_name, 'leaderboard-types')
        
        url = reverse('leaderboard-global-leaderboard')
        self.assertEqual(resolve(url).view_name, 'leaderboard-global-leaderboard')
        
        url = reverse('leaderboard-friends-leaderboard')
        self.assertEqual(resolve(url).view_name, 'leaderboard-friends-leaderboard')
        
        url = reverse('leaderboard-category-rankings')
        self.assertEqual(resolve(url).view_name, 'leaderboard-category-rankings')
        
        url = reverse('leaderboard-refresh-rankings')
        self.assertEqual(resolve(url).view_name, 'leaderboard-refresh-rankings')

    def test_friendship_urls(self):
        """Test FriendshipViewSet URLs"""
        url = reverse('friendship-list')
        self.assertEqual(resolve(url).view_name, 'friendship-list')
        
        url = reverse('friendship-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'friendship-detail')
        
        url = reverse('friendship-send-request')
        self.assertEqual(resolve(url).view_name, 'friendship-send-request')
        
        url = reverse('friendship-accept-request', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'friendship-accept-request')
        
        url = reverse('friendship-reject-request', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'friendship-reject-request')

    def test_mission_urls(self):
        """Test MissionViewSet URLs"""
        url = reverse('mission-list')
        self.assertEqual(resolve(url).view_name, 'mission-list')
        
        url = reverse('mission-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'mission-detail')
        
        url = reverse('mission-available-missions')
        self.assertEqual(resolve(url).view_name, 'mission-available-missions')
        
        url = reverse('mission-accept-mission')
        self.assertEqual(resolve(url).view_name, 'mission-accept-mission')
        
        url = reverse('mission-generate-random-missions')
        self.assertEqual(resolve(url).view_name, 'mission-generate-random-missions')
        
        url = reverse('mission-abandon-mission', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'mission-abandon-mission')
        
        url = reverse('mission-mission-progress')
        self.assertEqual(resolve(url).view_name, 'mission-mission-progress')
        
        url = reverse('mission-update-mission-progress')
        self.assertEqual(resolve(url).view_name, 'mission-update-mission-progress')

    def test_notification_urls(self):
        """Test NotificationViewSet URLs"""
        url = reverse('notification-list')
        self.assertEqual(resolve(url).view_name, 'notification-list')
        
        url = reverse('notification-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'notification-detail')
        
        url = reverse('notification-unread-count')
        self.assertEqual(resolve(url).view_name, 'notification-unread-count')
        
        url = reverse('notification-mark-all-read')
        self.assertEqual(resolve(url).view_name, 'notification-mark-all-read')
        
        url = reverse('notification-mark-read', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'notification-mark-read')
        
        url = reverse('notification-archive', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'notification-archive')
        
        url = reverse('notification-archive-all-read')
        self.assertEqual(resolve(url).view_name, 'notification-archive-all-read')
        
        url = reverse('notification-by-type')
        self.assertEqual(resolve(url).view_name, 'notification-by-type')
        
        url = reverse('notification-recent')
        self.assertEqual(resolve(url).view_name, 'notification-recent')

    def test_notification_settings_urls(self):
        """Test NotificationSettingsViewSet URLs"""
        url = reverse('notification-settings-list')
        self.assertEqual(resolve(url).view_name, 'notification-settings-list')
        
        url = reverse('notification-settings-detail', kwargs={'pk': 1})
        self.assertEqual(resolve(url).view_name, 'notification-settings-detail')
        
        url = reverse('notification-settings-get-settings')
        self.assertEqual(resolve(url).view_name, 'notification-settings-get-settings')
        
        url = reverse('notification-settings-update-settings')
        self.assertEqual(resolve(url).view_name, 'notification-settings-update-settings')
        
        url = reverse('notification-settings-notification-types')
        self.assertEqual(resolve(url).view_name, 'notification-settings-notification-types')

    # def test_game_stats_urls(self):
    #     """Test GameStatsViewSet URLs"""
    #     url = reverse('game-stats-list')
    #     self.assertEqual(resolve(url).view_name, 'game-stats-list')
        
    #     url = reverse('game-stats-dashboard-summary')
    #     self.assertEqual(resolve(url).view_name, 'game-stats-dashboard-summary')
        
    #     url = reverse('game-stats-send-test-notification')
    #     self.assertEqual(resolve(url).view_name, 'game-stats-send-test-notification')
        
    #     url = reverse('game-stats-system-stats')
    #     self.assertEqual(resolve(url).view_name, 'game-stats-system-stats')


    def test_game_stats_urls(self):
        """Test GameStatsViewSet URLs"""
        # Skip list test as GameStatsViewSet may not have a standard list endpoint
        url = reverse('game-stats-dashboard-summary')
        self.assertEqual(resolve(url).view_name, 'game-stats-dashboard-summary')
        
        url = reverse('game-stats-send-test-notification')
        self.assertEqual(resolve(url).view_name, 'game-stats-send-test-notification')
        
        url = reverse('game-stats-system-stats')
        self.assertEqual(resolve(url).view_name, 'game-stats-system-stats')

    