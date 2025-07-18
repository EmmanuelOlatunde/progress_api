from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from ..models import (
    Task, ProgressProfile, XPLog, Achievement, 
    UserAchievement, LeaderboardType, LeaderboardEntry, 
    MissionTemplate, UserMission, WeeklyReview, Notification, 
    SystemSetting, Category
)

from ..gamification import GamificationEngine, LeaderboardService, MissionService, SystemService

User = get_user_model()


class GamificationEngineTests(TestCase):
    """Tests for the GamificationEngine class"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Development',
            xp_multiplier=1.5
        )
        self.engine = GamificationEngine(self.user)
    
    def create_task(self, difficulty='medium', priority='medium', due_date=None):
        """Helper method to create a task"""
        if due_date is None:
            due_date = timezone.now() + timedelta(days=1)
        
        return Task.objects.create(
            user=self.user,
            title='Test Task',
            description='Test description',
            category=self.category,
            difficulty=difficulty,
            priority=priority,
            due_date=due_date
        )
    
    @patch('progress.gamification.GamificationEngine.get_timing_modifier')
    def test_calculate_task_xp_basic(self, mock_get_timing_modifier):
        """Test basic task XP calculation with mocked timing"""
        # Mock the timing modifier to make the test deterministic
        mock_get_timing_modifier.return_value = 1.3
        
        task = self.create_task(difficulty='easy', priority='medium')
        xp = self.engine.calculate_task_xp(task)
        
        # Expected: 10 (easy) * 1.5 (category) * 1.1 (medium priority) * 1.3 (mocked timing)
        expected_xp = int(10 * 1.5 * 1.1 * 1.3) # 21.45 -> 21
        self.assertEqual(xp, expected_xp)

    
    @patch('progress.gamification.GamificationEngine.get_timing_modifier')
    def test_calculate_task_xp_difficulty_levels(self, mock_get_timing_modifier):
        """Test XP calculation for different difficulty levels"""
        # Mock the timing modifier to make the test deterministic
        mock_get_timing_modifier.return_value = 1.3
        
        difficulties = {
            'easy': 10,
            'medium': 20,
            'hard': 40,
            'expert': 100
        }
        
        for difficulty, base_xp in difficulties.items():
            task = self.create_task(difficulty=difficulty)
            xp = self.engine.calculate_task_xp(task)
            # Expected: base_xp * 1.5 (category) * 1.1 (priority) * 1.3 (timing)
            expected_xp = int(base_xp * 1.5 * 1.1 * 1.3)            
            self.assertEqual(xp, expected_xp, f"Failed for difficulty: {difficulty}")

    
    @patch('progress.gamification.GamificationEngine.get_timing_modifier')
    def test_calculate_task_xp_priority_bonus(self, mock_get_timing_modifier):
        """Test XP calculation for priority bonuses"""
        # Mock the timing modifier to make the test deterministic
        mock_get_timing_modifier.return_value = 1.3

        priority_bonus = {
            'low': 1.0,
            'medium': 1.1,
            'high': 1.25,
            'urgent': 2.5
        }
        
        for priority, multiplier in priority_bonus.items():
            task = self.create_task(priority=priority)
            xp = self.engine.calculate_task_xp(task)
            # Expected: 20 (medium) * 1.5 (category) * multiplier * 1.3 (timing)
            expected_xp = int(20 * 1.5 * multiplier * 1.3)
            self.assertEqual(xp, expected_xp, f"Failed for priority: {priority}")
    
    def test_timing_modifier_early_completion(self):
        due_date = timezone.now() + timedelta(days=2)
        task = self.create_task(due_date=due_date)
        with patch.object(task, 'created_at', timezone.now() - timedelta(days=4)):
            modifier = self.engine.get_timing_modifier(task)
            self.assertEqual(modifier, 1.15)  # 2/6=0.33 -> 1.15
    
    def test_timing_modifier_late_completion(self):
        due_date = timezone.now() + timedelta(days=4)
        # Create task 4 days before due date
        created_at = timezone.now()
        task = self.create_task(due_date=due_date)
        
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(days=5)):
            task = self.create_task(due_date=due_date)
            task.created_at = created_at
            task.save()
            
            modifier = self.engine.get_timing_modifier(task)
            # Calculation:
            # Total time = 4 days
            # Overdue time = 1 day
            # Overdue ratio = 1/4 = 0.25 -> "slightly late" penalty (0.8)
            self.assertEqual(modifier, 0.8)
    
    def test_timing_modifier_no_due_date(self):
        # Create task without helper to ensure due_date=None
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            description='Test',
            category=self.category,
            difficulty='medium',
            priority='medium',
            due_date=None
        )
        modifier = self.engine.get_timing_modifier(task)
        self.assertEqual(modifier, 1.0)
    
    def test_can_complete_task_timing_restriction(self):
        """Test task completion timing restrictions"""
        # Create an expert task (requires 1 day minimum)
        task = self.create_task(difficulty='expert')
        
        # Mock creation time to be 30 minutes ago
        with patch.object(task, 'created_at', timezone.now() - timedelta(minutes=30)):
            can_complete, message = self.engine.can_complete_task(task)
            self.assertFalse(can_complete)
            self.assertIn('Wait', message)
    
    def test_can_complete_task_sufficient_time(self):
        """Test task completion when sufficient time has passed"""
        # Create an easy task (requires 15 minutes minimum)
        task = self.create_task(difficulty='easy')
        
        # Mock creation time to be 20 minutes ago
        with patch.object(task, 'created_at', timezone.now() - timedelta(minutes=20)):
            can_complete, message = self.engine.can_complete_task(task)
            self.assertTrue(can_complete)
            self.assertEqual(message, "Task can be completed")
    
    def test_award_task_xp_success(self):
        """Test successful XP award for task completion"""
        task = self.create_task(difficulty='easy')
        
        # Mock creation time to be sufficient
        with patch.object(task, 'created_at', timezone.now() - timedelta(hours=1)):
            xp_earned, message = self.engine.award_task_xp(task)
            
            self.assertGreater(xp_earned, 0)
            self.assertIn('Task completed', message)
            
            # Check XP log was created
            xp_log = XPLog.objects.filter(user=self.user, action='task_complete').first()
            self.assertIsNotNone(xp_log)
            self.assertEqual(xp_log.xp_earned, xp_earned)
            
            # Check profile was updated
            self.engine.profile.refresh_from_db()
            self.assertEqual(self.engine.profile.total_xp, xp_earned)
    
    def test_award_task_xp_timing_restriction(self):
        """Test XP award rejection due to timing restrictions"""
        task = self.create_task(difficulty='expert')
        
        # Mock creation time to be too recent
        with patch.object(task, 'created_at', timezone.now() - timedelta(minutes=30)):
            xp_earned, message = self.engine.award_task_xp(task)
            
            self.assertEqual(xp_earned, 0)
            self.assertIn('Wait', message)
            
            # Check no XP log was created
            xp_log = XPLog.objects.filter(user=self.user, action='task_complete').first()
            self.assertIsNone(xp_log)
    
    def test_update_streak_first_time(self):
        """Test streak update for first-time user"""
        # Ensure profile has no previous activity
        self.engine.profile.last_activity_date = None
        self.engine.profile.current_streak = 0
        self.engine.profile.save()
        
        streak_bonus = self.engine.update_streak()
        
        self.engine.profile.refresh_from_db()
        self.assertEqual(self.engine.profile.current_streak, 1)
        self.assertEqual(self.engine.profile.last_activity_date, timezone.now().date())
        self.assertEqual(streak_bonus, 0)  # No bonus for first day
    
    def test_update_streak_continuation(self):
        """Test streak continuation"""
        yesterday = timezone.now().date() - timedelta(days=1)
        self.engine.profile.last_activity_date = yesterday
        self.engine.profile.current_streak = 1
        self.engine.profile.save()
        
        streak_bonus = self.engine.update_streak()
        
        self.engine.profile.refresh_from_db()
        self.assertEqual(self.engine.profile.current_streak, 2)
        self.assertEqual(self.engine.profile.last_activity_date, timezone.now().date())
        self.assertEqual(streak_bonus, 0)  # No bonus until day 7
    
    def test_update_streak_seven_day_bonus(self):
        """Test streak bonus at 7 days"""
        yesterday = timezone.now().date() - timedelta(days=1)
        self.engine.profile.last_activity_date = yesterday
        self.engine.profile.current_streak = 6
        self.engine.profile.save()
        
        streak_bonus = self.engine.update_streak()
        
        self.engine.profile.refresh_from_db()
        self.assertEqual(self.engine.profile.current_streak, 7)
        self.assertEqual(streak_bonus, 35)  # 7 * 5 = 35
        
        # Check streak bonus XP log was created
        xp_log = XPLog.objects.filter(user=self.user, action='streak_bonus').first()
        self.assertIsNotNone(xp_log)
        self.assertEqual(xp_log.xp_earned, 35)
    
    def test_update_streak_broken(self):
        """Test streak breaking"""
        three_days_ago = timezone.now().date() - timedelta(days=3)
        self.engine.profile.last_activity_date = three_days_ago
        self.engine.profile.current_streak = 5
        self.engine.profile.longest_streak = 5
        self.engine.profile.save()
        
        streak_bonus = self.engine.update_streak()
        
        self.engine.profile.refresh_from_db()
        self.assertEqual(self.engine.profile.current_streak, 1)  # Reset to 1
        self.assertEqual(self.engine.profile.longest_streak, 5)  # Longest remains
        self.assertEqual(streak_bonus, 0)
    
    def test_update_streak_same_day_no_duplicate(self):
        """Test that streak doesn't update multiple times on same day"""
        today = timezone.now().date()
        self.engine.profile.last_activity_date = today
        self.engine.profile.current_streak = 3
        self.engine.profile.save()
        
        streak_bonus = self.engine.update_streak()
        
        self.engine.profile.refresh_from_db()
        self.assertEqual(self.engine.profile.current_streak, 3)  # No change
        self.assertEqual(streak_bonus, 0)
    
    def test_recalculate_streak(self):
        """Test streak recalculation from task history"""
        # Create tasks on consecutive days
        base_date = timezone.now() - timedelta(days=5)
        
        for i in range(3):  # 3 consecutive days
            task = self.create_task()
            task.is_completed = True
            task.completed_at = base_date + timedelta(days=i)
            task.save()
        
        # Add a task after a gap (should break streak)
        task = self.create_task()
        task.is_completed = True
        task.completed_at = base_date + timedelta(days=5)  # 2-day gap
        task.save()
        
        result = self.engine.recalculate_streak()
        
        self.assertEqual(result['current_streak'], 1)  # Only the last task
        self.assertEqual(result['longest_streak'], 3)  # The 3 consecutive days
    
    def test_get_timing_status_messages(self):
        """Test timing status message generation"""
        # Test early completion with safe margin (5/8 = 0.625 > 0.5)
        due_date = timezone.now() + timedelta(days=5)
        task = self.create_task(due_date=due_date)
        
        with patch.object(task, 'created_at', timezone.now() - timedelta(days=3)):
            status = self.engine.get_timing_status(task)
            self.assertEqual(status, "completed early - bonus XP!")

        # Add new test for boundary condition
        def test_boundary_condition(self):
            base_time = timezone.now()
            with patch('progress.gamification.timezone.now') as mock_now:  # Adjust module path
                mock_now.return_value = base_time
                task = self.create_task(
                    due_date=base_time + timedelta(days=4),
                    created_at=base_time - timedelta(days=4)
                )
                status = self.engine.get_timing_status(task)
                self.assertEqual(status, "completed early - bonus XP!")
            
    
    def test_generate_weekly_review(self):
        """Test weekly review generation"""
        # Create some completed tasks for the week
        base_date = timezone.now() - timedelta(days=6)  # Ensure within 7 days
        
        for i in range(5):
            task = self.create_task(difficulty='medium')
            task.is_completed = True
            task.completed_at = base_date + timedelta(days=i)
            task.save()
            
            # Create corresponding XP log
            XPLog.objects.create(
                user=self.user,
                action='task_complete',
                xp_earned=30,
                task=task,
                created_at=task.completed_at
            )
        
        review = self.engine.generate_weekly_review()
        
        self.assertIsInstance(review, WeeklyReview)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.total_tasks, 5)
        self.assertEqual(review.total_xp, 150)  # 5 * 30
        self.assertGreater(review.performance_score, 0)
        self.assertIsNotNone(review.suggestions)
    
    def test_check_achievements(self):
        """Test achievement checking and unlocking"""
        # Create a task count achievement
        achievement = Achievement.objects.create(
            name='Task Master',
            description='Complete 5 tasks',
            achievement_type='task_count',
            threshold=5,
            xp_reward=100
        )
        
        # Create 5 completed tasks
        for i in range(5):
            task = self.create_task()
            task.is_completed = True
            task.save()
        
        newly_unlocked = self.engine.check_all_achievements()
        
        self.assertEqual(len(newly_unlocked), 1)
        self.assertEqual(newly_unlocked[0], achievement)
        
        # Check user achievement was created
        user_achievement = UserAchievement.objects.filter(
            user=self.user, 
            achievement=achievement
        ).first()
        self.assertIsNotNone(user_achievement)
        
        # Check XP log was created
        xp_log = XPLog.objects.filter(
            user=self.user,
            action='achievement'
        ).first()
        self.assertIsNotNone(xp_log)
        self.assertEqual(xp_log.xp_earned, 100)


class LeaderboardServiceTests(TestCase):
    """Tests for the LeaderboardService class"""
    
    def setUp(self):
        self.leaderboard_type = LeaderboardType.objects.create(
            name='Test Leaderboard',
            leaderboard_type='global'
        )
        period_start = timezone.now() - timedelta(days=7)
        period_end = timezone.now()
        
        # Clear any existing entries
        LeaderboardEntry.objects.filter(leaderboard_type=self.leaderboard_type).delete()
        
        # Create test users and entries
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com')
        self.user3 = User.objects.create_user(username='user3', email='user3@example.com')
        self.category = Category.objects.create(
            name='Development',
            xp_multiplier=1.0
        )
        LeaderboardEntry.objects.create(
            leaderboard_type=self.leaderboard_type,
            user=self.user1,
            period_start=period_start,
            period_end=period_end,
            rank=1,
            score=100
        )
        
        LeaderboardEntry.objects.create(
            leaderboard_type=self.leaderboard_type,
            user=self.user2,
            period_start=period_start,
            period_end=period_end,
            rank=5,
            score=20
        )

    
    def test_calculate_user_scores(self):
        """Test user score calculation"""
        # Create tasks for both users
        Task.objects.create(
            user=self.user1,
            title='Task 1',
            category=self.category,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=1)
        )
        
        Task.objects.create(
            user=self.user2,
            title='Task 2',
            category=self.category,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=2)
        )
        
        # Create XP logs
        XPLog.objects.create(
            user=self.user1,
            action='task_complete',
            xp_earned=50,
            created_at=timezone.now() - timedelta(days=1)
        )
        
        XPLog.objects.create(
            user=self.user2,
            action='task_complete',
            xp_earned=75,
            created_at=timezone.now() - timedelta(days=2)
        )
        
        start_date = timezone.now() - timedelta(days=7)
        end_date = timezone.now()
        
        scores = LeaderboardService._calculate_user_scores(start_date, end_date)
        
        self.assertIn(self.user1.id, scores)
        self.assertIn(self.user2.id, scores)
        
        # User2 should have higher score due to more XP and higher streak
        user1_score = scores[self.user1.id]['total_score']
        user2_score = scores[self.user2.id]['total_score']
        self.assertGreater(user2_score, user1_score)
    
    def test_update_rankings(self):
        """Test leaderboard ranking updates"""
        # Create some task activity
        Task.objects.create(
            user=self.user1,
            title='Task 1',
            category=self.category,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=1)
        )
        
        XPLog.objects.create(
            user=self.user1,
            action='task_complete',
            xp_earned=50,
            created_at=timezone.now() - timedelta(days=1)
        )
        
        LeaderboardService.update_rankings('weekly')
        
        # Check that leaderboard type was created
        leaderboard_type = LeaderboardType.objects.filter(
            name='Weekly Global Leaderboard'
        ).first()
        self.assertIsNotNone(leaderboard_type)
        
        # Check that entry was created
        entry = LeaderboardEntry.objects.filter(
            leaderboard_type=leaderboard_type,
            user=self.user1
        ).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.rank, 1)
    
    def test_get_leaderboard(self):
        """Test getting leaderboard data"""
        leaderboard = LeaderboardService.get_leaderboard('global', limit=10)
        
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]['rank'], 1)
        self.assertEqual(leaderboard[0]['user'], self.user1)
        self.assertEqual(leaderboard[1]['rank'], 5)
        self.assertEqual(leaderboard[1]['user'], self.user2)
    
    def test_get_user_rank(self):
        """Test getting user's rank"""
        
        rank = LeaderboardService.get_user_rank(self.user1.id, 'global')
        self.assertEqual(rank, 1)
        
        # Test user not in leaderboard
        rank = LeaderboardService.get_user_rank(self.user3.id, 'global')
        self.assertIsNone(rank)
    
    def test_get_user_position_context(self):
        """Test getting user position with context"""
        leaderboard_type = LeaderboardType.objects.create(
            name='Test Leaderboard',
            leaderboard_type='global'
        )
        # Define the period for the leaderboard entries
        period_start = timezone.now() - timedelta(days=7)
        period_end = timezone.now()
        
        # Create entries for ranks 1-10
        users = []
        for i in range(10):
            user, _ = User.objects.get_or_create(
                username=f'user{i}',
                email=f'user{i}@example.com'
            )
            users.append(user)
            
            LeaderboardEntry.objects.create(
                leaderboard_type=leaderboard_type,
                user=user,
                rank=i + 1,
                score=100 - i,
                period_start=period_start,
                period_end=period_end
            )
        
        # Get context for user at rank 5
        context = LeaderboardService.get_user_position_context(users[4].id, 'global')
        
        self.assertEqual(context['user_rank'], 5)
        self.assertGreater(len(context['context']), 0)
        
        # Should include users around rank 5
        ranks_in_context = [entry['rank'] for entry in context['context']]
        self.assertIn(5, ranks_in_context)
        self.assertTrue(any(entry['is_current_user'] for entry in context['context']))


class MissionServiceTests(TestCase):
    """Tests for the MissionService class"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='Testuser@example.com')
        self.profile = ProgressProfile.objects.get(user_id=self.user.id)
        self.profile.current_level=1
        self.profile.total_xp=100
        self.profile.save()
    
        # Create 5 daily mission templates
        self.templates = []
        for i in range(5):
            template = MissionTemplate.objects.create(
                name=f'Complete {i+1} tasks',
                description=f'Sample daily mission {i+1}',
                mission_type='daily_goal',
                difficulty='easy',
                target_value=3 + i,
                xp_reward=10 + (i * 5),
                min_user_level=1,
                max_user_level=10,
                is_active=True
            )
            self.templates.append(template)

    def test_assign_daily_missions(self):
        """Test daily mission assignment"""
        self.assertEqual(MissionTemplate.objects.filter(mission_type='daily_goal', is_active=True).count(), 5)
        missions = MissionService.assign_daily_missions(self.user.id)
        
        # Check mission assignment
        self.assertGreater(len(missions), 0, "No missions were assigned")
        self.assertLessEqual(len(missions), 5, "Too many missions assigned")
        
        for mission in missions:
            self.assertEqual(mission.user, self.user)
            self.assertEqual(mission.template.mission_type, 'daily_goal')
            self.assertEqual(mission.created_at.date(), timezone.now().date())
            self.assertFalse(mission.is_completed)
    
    def test_assign_daily_missions_no_duplicates(self):
        """Test that daily missions aren't duplicated"""
        # Assign missions first time
        missions1 = MissionService.assign_daily_missions(self.user.id)
        
        # Try to assign again on same day
        missions2 = MissionService.assign_daily_missions(self.user.id)
        
        # Should return same missions
        self.assertEqual(len(missions1), len(missions2))
        self.assertEqual(set(m.id for m in missions1), set(m.id for m in missions2))
    
    def test_calculate_target_value(self):
        """Test target value calculation based on user level"""
        # Test with level 1 user
        low_level_user = User.objects.create_user(username='lowlevel', email='low@test.com')
        low_level_profile=low_level_user.progress_profile
        low_level_profile.current_level=1
        low_level_profile.total_xp=0
        low_level_profile.save()
        
        target = MissionService._calculate_target_value(self.templates[0], low_level_profile)
        self.assertGreaterEqual(target, 1)
        
        # Test with higher level user

        high_level_user = User.objects.create_user(username='highlevel', email='high@test.com')
        high_level_profile=high_level_user.progress_profile
        high_level_profile.current_level=5
        high_level_profile.total_xp=1000
        high_level_profile.save()

        high_target = MissionService._calculate_target_value(self.templates[0], high_level_profile)
        self.assertGreater(high_target, target)  # Should be higher for higher level
    
    def test_update_mission_progress(self):
        """Test mission progress updates"""
        # Create a mission
        mission = UserMission.objects.create(
            user=self.user,
            template=self.templates[0],
            created_at=timezone.now().date(),
            target_value=3,
            current_progress=0,
            xp_reward=50,
            status='active',
            end_date=timezone.now() + timedelta(hours=1)
        )
        
        # Update progress
        completed = MissionService.update_mission_progress(
            self.user.id, 
            mission_type='daily_goal',
            progress_value=2
        )
        
        mission.refresh_from_db()
        self.assertEqual(mission.current_progress, 2)
        self.assertFalse(mission.is_completed)
        self.assertEqual(len(completed), 0)
        
        # Complete the mission
        completed = MissionService.update_mission_progress(
            self.user.id, 
            mission_type='daily_goal', 
            progress_value=1
        )
        
        mission.refresh_from_db()
        self.assertEqual(mission.current_progress, 3)
        self.assertTrue(mission.is_completed)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0], mission)
        
        # Check XP was awarded
        xp_log = XPLog.objects.filter(
            user=self.user,
            action='mission_complete'
        ).first()
        self.assertIsNotNone(xp_log)
        self.assertEqual(xp_log.xp_earned, 50)
    
    def test_get_user_missions(self):
        """Test getting user missions"""
        # Create missions
        mission1 = UserMission.objects.create(
            user=self.user,
            template=self.templates[0],
            created_at=timezone.now().date(),
            target_value=3,
            xp_reward=50,
            end_date=timezone.now() + timedelta(days=2)
        )
        
        UserMission.objects.create(
            user=self.user,
            template=self.templates[1],
            created_at=timezone.now().date(),
            target_value=100,
            xp_reward=25,
            end_date=timezone.now() + timedelta(days=2)
        )
        
        # Get all missions
        all_missions = MissionService.get_user_missions(self.user.id)
        self.assertEqual(len(all_missions), 2)
        
        # Get daily missions only
        daily_missions = MissionService.get_user_missions(self.user.id, 'daily_goal')
        self.assertEqual(len(daily_missions), 2)
        self.assertEqual(daily_missions[0].user, mission1.user)


class SystemServiceTestCase(TestCase):
    """Test cases for SystemService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.active_user = User.objects.create_user(
            username='activeuser',
            email='active@example.com',
            password='testpass123',
            last_login=timezone.now() - timedelta(days=1)
        )
        
        self.inactive_user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='testpass123',
            last_login=timezone.now() - timedelta(days=10)
        )
    
    def test_get_setting_existing(self):
        """Test getting an existing system setting"""
        # Create a test setting
        SystemSetting.objects.create(
            key='test_key',
            value='test_value',
            description='Test setting'
        )
        
        result = SystemService.get_setting('test_key')
        self.assertEqual(result, 'test_value')
    
    def test_get_setting_non_existing_with_default(self):
        """Test getting non-existing setting with default value"""
        result = SystemService.get_setting('non_existing_key', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_get_setting_non_existing_without_default(self):
        """Test getting non-existing setting without default value"""
        result = SystemService.get_setting('non_existing_key')
        self.assertIsNone(result)
    
    def test_set_setting_new(self):
        """Test setting a new system setting"""
        result = SystemService.set_setting('new_key', 'new_value', 'New setting')
        
        self.assertIsInstance(result, SystemSetting)
        self.assertEqual(result.key, 'new_key')
        self.assertEqual(result.value, 'new_value')
        self.assertEqual(result.description, 'New setting')
        
        # Verify it was saved to database
        saved_setting = SystemSetting.objects.get(key='new_key')
        self.assertEqual(saved_setting.value, 'new_value')
    
    def test_set_setting_update_existing(self):
        """Test updating an existing system setting"""
        # Create initial setting
        SystemSetting.objects.create(
            key='existing_key',
            value='old_value',
            description='Old description'
        )
        
        result = SystemService.set_setting('existing_key', 'new_value', 'New description')
        
        self.assertEqual(result.key, 'existing_key')
        self.assertEqual(result.value, 'new_value')
        self.assertEqual(result.description, 'New description')
        
        # Verify only one record exists
        settings_count = SystemSetting.objects.filter(key='existing_key').count()
        self.assertEqual(settings_count, 1)
    
    def test_set_setting_different_value_types(self):
        """Test setting different types of values"""
        # Test integer
        result_int = SystemService.set_setting('int_key', 42)
        self.assertEqual(result_int.value, '42')
        
        # Test boolean
        result_bool = SystemService.set_setting('bool_key', True)
        self.assertEqual(result_bool.value, 'True')
        
        # Test float
        result_float = SystemService.set_setting('float_key', 3.14)
        self.assertEqual(result_float.value, '3.14')
    
    @patch('progress.gamification.SystemService.set_setting')
    @patch('progress.gamification.MissionService.assign_daily_missions')
    @patch('progress.gamification.LeaderboardService.update_rankings')
    def test_run_daily_maintenance_success(self, mock_update_rankings, mock_assign_missions, mock_set_setting):
        mock_update_rankings.return_value = True
        mock_assign_missions.return_value = ['mission1', 'mission2']
        mock_set_setting.return_value = MagicMock()
        
        fixed_now = timezone.now()
        with patch('django.utils.timezone.now', return_value=fixed_now):
            # Create notifications with explicit created_at updates
            old_notification = Notification.objects.create(
                user=self.user,
                title='Old notification',
                message='Old message',
            )
            old_notification.created_at = fixed_now - timedelta(days=35)
            old_notification.save(update_fields=['created_at'])
            
            recent_notification = Notification.objects.create(
                user=self.user,
                title='Recent notification',
                message='Recent message',
            )
            recent_notification.created_at = fixed_now - timedelta(days=5)
            recent_notification.save(update_fields=['created_at'])
            
            # Run maintenance
            result = SystemService.run_daily_maintenance()
        
        self.assertTrue(result['leaderboards_updated'])
        self.assertEqual(result['missions_assigned'], 2)
        self.assertEqual(result['notifications_cleaned'], 1)
        self.assertNotIn('error', result)
        
        mock_update_rankings.assert_called_once_with('daily')
        mock_assign_missions.assert_called_once_with(self.active_user.id)
        
        self.assertFalse(Notification.objects.filter(id=old_notification.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent_notification.id).exists())
        
        mock_set_setting.assert_called_once()

    @patch('progress.gamification.LeaderboardService.update_rankings')
    def test_run_daily_maintenance_with_error(self, mock_update_rankings):
        """Test daily maintenance with error handling"""
        # Mock to raise an exception
        mock_update_rankings.side_effect = Exception('Test error')
        
        result = SystemService.run_daily_maintenance()
        
        # Verify error is captured
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Test error')
        self.assertFalse(result['leaderboards_updated'])
    
    def test_run_daily_maintenance_active_users_filter(self):
        """Test that daily maintenance only processes active users"""
        with patch('progress.gamification.MissionService.assign_daily_missions') as mock_assign:
            mock_assign.return_value = ['mission1']
            
            with patch('progress.gamification.LeaderboardService.update_rankings'):
                result = SystemService.run_daily_maintenance()
                
                # Should only call assign_daily_missions for active user
                mock_assign.assert_called_once_with(self.active_user.id)
                self.assertEqual(result['missions_assigned'], 1)
    

    def test_run_daily_maintenance_notification_cleanup(self):
        fixed_now = timezone.now()
        with patch('django.utils.timezone.now', return_value=fixed_now):
            # Create notifications with explicit created_at updates
            very_old = Notification.objects.create(
                user=self.user,
                title='Very old',
                message='Message',
            )
            very_old.created_at = fixed_now - timedelta(days=45)
            very_old.save(update_fields=['created_at'])
            
            old = Notification.objects.create(
                user=self.user,
                title='Old',
                message='Message',
            )
            old.created_at = fixed_now - timedelta(days=31)
            old.save(update_fields=['created_at'])
            
            borderline = Notification.objects.create(
                user=self.user,
                title='Borderline',
                message='Message',
            )
            borderline.created_at = fixed_now - timedelta(days=30)
            borderline.save(update_fields=['created_at'])
            
            recent = Notification.objects.create(
                user=self.user,
                title='Recent',
                message='Message',
            )
            recent.created_at = fixed_now - timedelta(days=15)
            recent.save(update_fields=['created_at'])
            
            with patch('progress.gamification.LeaderboardService.update_rankings'):
                with patch('progress.gamification.MissionService.assign_daily_missions', return_value=[]):
                    result = SystemService.run_daily_maintenance()
        
        # Check deletions
        self.assertFalse(Notification.objects.filter(id=very_old.id).exists())
        self.assertFalse(Notification.objects.filter(id=old.id).exists())
        self.assertTrue(Notification.objects.filter(id=borderline.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent.id).exists())
        
        # Should have cleaned 2 notifications (very_old, old)
        self.assertEqual(result['notifications_cleaned'], 2)  

    def test_run_daily_maintenance_no_active_users(self):
        """Test daily maintenance when no active users exist"""
        # Make all users inactive
        User.objects.update(last_login=timezone.now() - timedelta(days=10))
        
        with patch('progress.gamification.LeaderboardService.update_rankings'):
            with patch('progress.gamification.MissionService.assign_daily_missions') as mock_assign:
                result = SystemService.run_daily_maintenance()
                
                # Should not call assign_daily_missions
                mock_assign.assert_not_called()
                self.assertEqual(result['missions_assigned'], 0)
    
    def test_run_daily_maintenance_no_old_notifications(self):
        """Test daily maintenance when no old notifications exist"""
        # Create only recent notifications
        Notification.objects.create(
            user=self.user,
            title='Recent',
            message='Message',
            created_at=timezone.now() - timedelta(days=5)
        )
        
        with patch('progress.gamification.LeaderboardService.update_rankings'):
            with patch('progress.gamification.MissionService.assign_daily_missions', return_value=[]):
                result = SystemService.run_daily_maintenance()
                
                self.assertEqual(result['notifications_cleaned'], 0)

class SystemServiceIntegrationTestCase(TestCase):
    """Integration tests for SystemService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            last_login=timezone.now() - timedelta(days=1)
        )
    
    def test_setting_persistence(self):
        """Test that settings persist across get/set operations"""
        # Set a setting
        SystemService.set_setting('test_persistence', 'persistent_value', 'Test persistence')
        
        # Get it back
        result = SystemService.get_setting('test_persistence')
        self.assertEqual(result, 'persistent_value')
        
        # Update it
        SystemService.set_setting('test_persistence', 'updated_value', 'Updated description')
        
        # Get updated value
        result = SystemService.get_setting('test_persistence')
        self.assertEqual(result, 'updated_value')
    
    def test_maintenance_run_tracking(self):
        """Test that maintenance run is tracked in system settings"""
        with patch('progress.gamification.LeaderboardService.update_rankings'):
            with patch('progress.gamification.MissionService.assign_daily_missions', return_value=[]):
                SystemService.run_daily_maintenance()
                
                # Check that last maintenance run was recorded
                last_run = SystemService.get_setting('last_maintenance_run')
                self.assertIsNotNone(last_run)
                
                # Should be a valid ISO timestamp
                parsed_time = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                self.assertIsInstance(parsed_time, datetime)

# Additional test utilities
class SystemServiceTestUtils:
    """Utility methods for testing SystemService"""
    
    @staticmethod
    def create_test_notifications(user, count=5, days_old=35):
        """Create test notifications for cleanup testing"""
        notifications = []
        for i in range(count):
            notification = Notification.objects.create(
                user=user,
                title=f'Test notification {i}',
                message=f'Test message {i}',
                created_at=timezone.now() - timedelta(days=days_old)
            )
            notifications.append(notification)
        return notifications
    
    @staticmethod
    def create_active_users(count=3):
        """Create active users for testing"""
        users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'active_user_{i}',
                email=f'active{i}@example.com',
                password='testpass123',
                last_login=timezone.now() - timedelta(days=1)
            )
            users.append(user)
        return users

