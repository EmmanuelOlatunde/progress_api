from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import random
from typing import List, Dict, Optional
from .models import (
    LeaderboardType, LeaderboardEntry, 
    MissionTemplate, UserMission, WeeklyReview,
    Notification, Task, XPLog, ProgressProfile,
    SystemSetting, Achievement, UserAchievement
)

User = get_user_model()


class GamificationEngine:
    def __init__(self, user):
        self.user = user
        self.profile, created = ProgressProfile.objects.get_or_create(user=user)

    def calculate_task_xp(self, task):
        """Calculate XP value for a task based on difficulty, category, and timing"""
        base_xp = {
            'easy': 10,
            'medium': 20,
            'hard': 40,
            'expert': 100
        }
        
        xp = base_xp.get(task.difficulty, 25)
        
        # Apply category multiplier
        xp = int(xp * task.category.xp_multiplier)
        
        # Priority bonus
        priority_bonus = {
            'low': 1.0,
            'medium': 1.1,
            'high': 1.25,
            'urgent': 2.5
        }
        xp = int(xp * priority_bonus.get(task.priority, 1.0))
        
        # Apply timing modifier
        timing_modifier = self.get_timing_modifier(task)
        xp = int(xp * timing_modifier)
        
        return max(xp, 1)  # Ensure minimum 1 XP

    def get_timing_modifier(self, task):
        """Calculate timing-based XP modifier"""
        if not task.due_date:
            return 1.0  # No modifier if no due date
        
        now = timezone.now()
        time_to_due = task.due_date - now
        
        # Calculate percentage of time remaining
        total_time = task.due_date - task.created_at
        time_remaining_ratio = time_to_due.total_seconds() / total_time.total_seconds()
        
        # Early completion bonus (completed with 50%+ time remaining)
        if time_remaining_ratio >= 0.5:
            return 1.3  # 30% bonus
        # Good timing (completed with 25-50% time remaining)
        elif time_remaining_ratio >= 0.25:
            return 1.15  # 15% bonus
        # On time (completed with 0-25% time remaining)
        elif time_remaining_ratio >= 0:
            return 1.0  # Normal XP
        # Late completion penalties
        elif time_remaining_ratio >= -0.25:  # Up to 25% late
            return 0.8  # 20% penalty
        elif time_remaining_ratio >= -0.5:   # Up to 50% late
            return 0.6  # 40% penalty
        else:  # Very late (more than 50% overdue)
            return 0.4  # 60% penalty

    def can_complete_task(self, task):
        """Check if task can be completed based on timing restrictions"""
        if not task.due_date:
            return True, "Task can be completed"
        
        now = timezone.now()
        
        # Define minimum time requirements based on difficulty
        min_time_requirements = {
            'easy': timedelta(minutes=15),    # Easy tasks need at least 15 minutes
            'medium': timedelta(hours=1),     # Medium tasks need at least 1 hour
            'hard': timedelta(hours=4),       # Hard tasks need at least 4 hours
            'expert': timedelta(days=1)       # Expert tasks need at least 1 day
        }
        
        min_time = min_time_requirements.get(task.difficulty, timedelta(hours=1))
        time_since_created = now - task.created_at
        
        if time_since_created < min_time:
            remaining_time = min_time - time_since_created
            hours = remaining_time.total_seconds() // 3600
            minutes = (remaining_time.total_seconds() % 3600) // 60
            
            if hours > 0:
                wait_time = f"{int(hours)} hours and {int(minutes)} minutes"
            else:
                wait_time = f"{int(minutes)} minutes"
                
            return False, f"Task created too recently. Wait {wait_time} before completing this {task.difficulty} task."
        
        return True, "Task can be completed"

    def award_task_xp(self, task):
        """Award XP for completing a task with timing considerations"""
        # Check if task can be completed
        can_complete, message = self.can_complete_task(task)
        if not can_complete:
            return 0, message
        
        xp_earned = self.calculate_task_xp(task)
        
        # Update streak BEFORE checking for bonus to ensure proper counting
        streak_bonus = self.update_streak()
        if streak_bonus > 0:
            xp_earned += streak_bonus

        # Determine timing status for logging
        timing_status = self.get_timing_status(task)
        
        # Create XP log entry
        XPLog.objects.create(
            user=self.user,
            action='task_complete',
            xp_earned=xp_earned,
            task=task,
            description=f"Completed {task.get_difficulty_display().lower()} task in {task.category.name} ({timing_status})"
        )

        # Update profile
        self.profile.total_xp += xp_earned
        self.profile.save()
        self.profile.update_level()

        # Check achievements
        self.check_all_achievements()

        return xp_earned, f"Task completed! Earned {xp_earned} XP ({timing_status})"

    def get_timing_status(self, task):
        """Get human-readable timing status"""
        if not task.due_date:
            return "no deadline"
        
        now = timezone.now()
        time_to_due = task.due_date - now
        total_time = task.due_date - task.created_at
        time_remaining_ratio = time_to_due.total_seconds() / total_time.total_seconds()
        
        if time_remaining_ratio >= 0.5:
            return "completed early - bonus XP!"
        elif time_remaining_ratio >= 0.25:
            return "good timing - bonus XP!"
        elif time_remaining_ratio >= 0:
            return "completed on time"
        elif time_remaining_ratio >= -0.25:
            return "slightly late - XP penalty"
        elif time_remaining_ratio >= -0.5:
            return "late - XP penalty"
        else:
            return "very late - major XP penalty"

    def update_streak(self):
        """Update daily streak and return bonus XP - FIXED VERSION"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        print(f"DEBUG: Today: {today}")
        print(f"DEBUG: Last activity: {self.profile.last_activity_date}")
        print(f"DEBUG: Current streak: {self.profile.current_streak}")
        
        # FIXED: Check if we've already processed streak for today
        if self.profile.last_activity_date == today:
            print("DEBUG: Already counted today - no streak update")
            return 0
        
        streak_bonus = 0
        
        # FIXED: Proper streak logic
        if self.profile.last_activity_date is None:
            # First time completing a task
            self.profile.current_streak = 1
            print("DEBUG: Starting first streak")
        elif self.profile.last_activity_date == yesterday:
            # Continue streak - completed task yesterday and now today
            self.profile.current_streak += 1
            print(f"DEBUG: Continuing streak to {self.profile.current_streak}")
        else:
            # Streak broken - start new streak
            self.profile.current_streak = 1
            print("DEBUG: Streak broken - starting new streak")
        
        # Update longest streak
        if self.profile.current_streak > self.profile.longest_streak:
            self.profile.longest_streak = self.profile.current_streak
            print(f"DEBUG: New longest streak: {self.profile.longest_streak}")
        
        # Calculate streak bonus (every 7 days)
        if self.profile.current_streak > 0 and self.profile.current_streak % 7 == 0:
            streak_bonus = self.profile.current_streak * 5
            print(f"DEBUG: Streak bonus: {streak_bonus}")
            
            XPLog.objects.create(
                user=self.user,
                action='streak_bonus',
                xp_earned=streak_bonus,
                description=f"{self.profile.current_streak}-day streak bonus!"
            )
        
        # FIXED: Always update last_activity_date to today
        self.profile.last_activity_date = today
        self.profile.save()
        print(f"DEBUG: Saved profile with streak: {self.profile.current_streak}")
        
        return streak_bonus

    # ADDED: Utility method to debug streak issues
    def debug_streak_status(self):
        """Debug method to check streak status and recent task completions"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # print(f"=== STREAK DEBUG INFO ===")
        # print(f"Today: {today}")
        # print(f"Profile last activity: {self.profile.last_activity_date}")
        # print(f"Current streak: {self.profile.current_streak}")
        # print(f"Longest streak: {self.profile.longest_streak}")
        
        # Check recent task completions
        recent_tasks = Task.objects.filter(
            user=self.user,
            is_completed=True,
            completed_at__date__gte=today - timedelta(days=7)
        ).order_by('-completed_at')
        
        #print(f"\nRecent completed tasks (last 7 days):")
        for task in recent_tasks:
            print(f"  - {task.title}: completed on {task.completed_at.date()}")
        
        # Check today's tasks
        today_tasks = Task.objects.filter(
            user=self.user,
            is_completed=True,
            completed_at__date=today
        )
        print(f"\nTasks completed today: {today_tasks.count()}")
        
        # Check yesterday's tasks
        yesterday_tasks = Task.objects.filter(
            user=self.user,
            is_completed=True,
            completed_at__date=yesterday
        )
        print(f"Tasks completed yesterday: {yesterday_tasks.count()}")
        
        return {
            'current_streak': self.profile.current_streak,
            'longest_streak': self.profile.longest_streak,
            'last_activity': self.profile.last_activity_date,
            'today_tasks': today_tasks.count(),
            'yesterday_tasks': yesterday_tasks.count()
        }

    # ADDED: Method to manually fix/reset streak if needed
    def recalculate_streak(self):
        """Recalculate streak based on actual task completion history"""
        # Get all completed tasks ordered by completion date
        completed_tasks = Task.objects.filter(
            user=self.user,
            is_completed=True
        ).order_by('completed_at')
        
        if not completed_tasks.exists():
            self.profile.current_streak = 0
            self.profile.longest_streak = 0
            self.profile.last_activity_date = None
            self.profile.save()
            return
        
        # Get unique completion dates
        completion_dates = list(set(
            task.completed_at.date() for task in completed_tasks
        ))
        completion_dates.sort()
        
        current_streak = 0
        longest_streak = 0
        last_date = None
        
        for date in completion_dates:
            if last_date is None or date == last_date + timedelta(days=1):
                # Start new streak or continue existing streak
                current_streak += 1
            else:
                # Streak broken
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
            
            last_date = date
        
        # Final check for longest streak
        longest_streak = max(longest_streak, current_streak)
        
        # Update profile
        self.profile.current_streak = current_streak
        self.profile.longest_streak = longest_streak
        self.profile.last_activity_date = completion_dates[-1] if completion_dates else None
        self.profile.save()
        
        print(f"Streak recalculated: Current={current_streak}, Longest={longest_streak}")
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_activity': self.profile.last_activity_date
        }

    def generate_weekly_review(self):
        """Generate weekly performance review and suggestions"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Get week's completed tasks
        week_tasks = Task.objects.filter(
            user=self.user,
            is_completed=True,
            completed_at__date__gte=start_date,
            completed_at__date__lte=end_date
        )
        
        # Calculate metrics
        total_tasks = week_tasks.count()
        total_xp = sum(log.xp_earned for log in XPLog.objects.filter(
            user=self.user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            action='task_complete'
        ))
        
        # Timing analysis
        early_tasks = 0
        on_time_tasks = 0
        late_tasks = 0
        
        for task in week_tasks.filter(due_date__isnull=False):
            if task.completed_at and task.due_date:
                if task.completed_at <= task.due_date:
                    time_ratio = (task.due_date - task.completed_at).total_seconds() / (task.due_date - task.created_at).total_seconds()
                    if time_ratio >= 0.25:
                        early_tasks += 1
                    else:
                        on_time_tasks += 1
                else:
                    late_tasks += 1
        
        # Category analysis
        category_performance = {}
        for task in week_tasks:
            cat_name = task.category.name
            if cat_name not in category_performance:
                category_performance[cat_name] = {'count': 0, 'total_xp': 0}
            category_performance[cat_name]['count'] += 1
            # Get XP for this specific task completion
            task_xp_log = XPLog.objects.filter(task=task, action='task_complete').first()
            if task_xp_log:
                category_performance[cat_name]['total_xp'] += task_xp_log.xp_earned
        
        # Generate suggestions
        suggestions = self.generate_suggestions(
            total_tasks, early_tasks, on_time_tasks, late_tasks, category_performance
        )
        
        # Calculate performance score (0-100)
        timing_score = 0
        if total_tasks > 0:
            timing_score = ((early_tasks * 2 + on_time_tasks * 1.5) / total_tasks) * 50
            timing_score = min(timing_score, 100)
        
        productivity_score = min((total_tasks / 7) * 20, 50)  # Up to 50 points for productivity
        performance_score = int(timing_score + productivity_score)
        
        # Create review record
        review = WeeklyReview.objects.create(
            user=self.user,
            week_start=start_date,
            week_end=end_date,
            total_tasks=total_tasks,
            total_xp=total_xp,
            early_completions=early_tasks,
            on_time_completions=on_time_tasks,
            late_completions=late_tasks,
            performance_score=performance_score,
            suggestions='\n'.join(suggestions),
            category_breakdown=category_performance
        )
        
        return review

    def generate_suggestions(self, total_tasks, early_tasks, on_time_tasks, late_tasks, category_performance):
        """Generate personalized improvement suggestions"""
        suggestions = []
        
        # Productivity suggestions
        if total_tasks < 5:
            suggestions.append("📈 Try to complete at least 5 tasks per week to maintain good productivity.")
        elif total_tasks >= 20:
            suggestions.append("🌟 Excellent productivity! You completed a high number of tasks this week.")
        
        # Timing suggestions
        total_timed_tasks = early_tasks + on_time_tasks + late_tasks
        if total_timed_tasks > 0:
            late_percentage = (late_tasks / total_timed_tasks) * 100
            early_percentage = (early_tasks / total_timed_tasks) * 100
            
            if late_percentage > 30:
                suggestions.append("⏰ Consider setting more realistic deadlines - 30%+ of your tasks were completed late.")
                suggestions.append("💡 Try breaking larger tasks into smaller, more manageable chunks.")
            elif early_percentage > 60:
                suggestions.append("🚀 Great time management! You're completing tasks early consistently.")
                suggestions.append("🎯 Consider taking on more challenging tasks to maximize your XP potential.")
            elif late_percentage == 0 and early_percentage > 0:
                suggestions.append("⭐ Perfect timing! No late completions this week - keep it up!")
        
        # Category suggestions
        if category_performance:
            most_productive_category = max(category_performance.items(), key=lambda x: x[1]['count'])
            least_productive_category = min(category_performance.items(), key=lambda x: x[1]['count'])
            
            if most_productive_category[1]['count'] >= 3:
                suggestions.append(f"🔥 You're crushing it in {most_productive_category[0]}! Consider leveraging this momentum.")
            
            if len(category_performance) > 1 and least_productive_category[1]['count'] == 1:
                suggestions.append(f"📚 Consider focusing more on {least_productive_category[0]} tasks for better balance.")
        
        # General motivation
        if not suggestions:
            suggestions.append("✨ Keep up the good work! Your task management is on track.")
        
        return suggestions

    def check_all_achievements(self):
        """Check all possible achievements for unlock"""
        achievements = Achievement.objects.all()
        newly_unlocked = []

        for achievement in achievements:
            if not UserAchievement.objects.filter(user=self.user, achievement=achievement).exists():
                progress = self.get_achievement_progress(achievement)
                
                if progress >= achievement.threshold:
                    self.unlock_achievement(achievement)
                    newly_unlocked.append(achievement)

        return newly_unlocked

    def get_achievement_progress(self, achievement):
        """Get current progress toward an achievement"""
        if achievement.achievement_type == 'task_count':
            return Task.objects.filter(user=self.user, is_completed=True).count()
        
        elif achievement.achievement_type == 'streak':
            return self.profile.longest_streak
        
        elif achievement.achievement_type == 'level':
            return self.profile.current_level
        
        elif achievement.achievement_type == 'xp':
            return self.profile.total_xp
        
        elif achievement.achievement_type == 'category':
            # Assuming threshold represents tasks completed in any single category
            category_counts = {}
            for task in Task.objects.filter(user=self.user, is_completed=True):
                category_counts[task.category_id] = category_counts.get(task.category_id, 0) + 1
            return max(category_counts.values()) if category_counts else 0
        
        elif achievement.achievement_type == 'timing':
            # New achievement type for timing-based rewards
            early_tasks = Task.objects.filter(
                user=self.user,
                is_completed=True,
                completed_at__lt=models.F('due_date')
            ).count()
            return early_tasks
        
        return 0

    def unlock_achievement(self, achievement):
        """Unlock an achievement and award XP"""
        user_achievement = UserAchievement.objects.create(
            user=self.user,
            achievement=achievement,
            progress=self.get_achievement_progress(achievement)
        )

        # Award achievement XP
        XPLog.objects.create(
            user=self.user,
            action='achievement',
            xp_earned=achievement.xp_reward,
            description=f"Unlocked achievement: {achievement.name}"
        )

        self.profile.total_xp += achievement.xp_reward
        self.profile.save()
        self.profile.update_level()

        return user_achievement

    def check_level_achievements(self, old_level, new_level):
        """Check for level-based achievements"""
        level_achievements = Achievement.objects.filter(
            achievement_type='level',
            threshold__lte=new_level,
            threshold__gt=old_level
        )

        for achievement in level_achievements:
            if not UserAchievement.objects.filter(user=self.user, achievement=achievement).exists():
                self.unlock_achievement(achievement)


class LeaderboardService:
    """Service for managing leaderboards and rankings"""
    

    @staticmethod
    def update_rankings(period: str = 'weekly') -> None:
        """Update leaderboard rankings for given period"""
        end_date = timezone.now()
        
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        # Get or create leaderboard type
        leaderboard_type, _ = LeaderboardType.objects.get_or_create(
            name=f'{period.title()} Global Leaderboard',
            leaderboard_type='global' if period == 'all_time' else period,
            defaults={'reset_frequency': period}
        )
        
        # Calculate user scores for the period
        user_scores = LeaderboardService._calculate_user_scores(start_date, end_date)
        
        # Update or create leaderboard entries
        for rank, (user_id, score_data) in enumerate(user_scores.items(), 1):
            entry, created = LeaderboardEntry.objects.update_or_create(
                leaderboard_type=leaderboard_type,
                user_id=user_id,
                period_start=start_date,
                period_end=end_date, 
                defaults={
                    'score': score_data['total_score'],
                    'rank': rank,
                    'tasks_completed': score_data['tasks_completed'],
                    'total_xp': score_data['total_xp'],
                    'streak_count': score_data['current_streak'],
                    'punctuality_rate': score_data['punctuality_rate']
                }
            )
    
    @staticmethod
    def _calculate_user_scores(start_date: datetime, end_date: datetime) -> Dict:
        """Calculate user scores for leaderboard period"""
        from .models import Task, ProgressProfile, XPLog
        
        # Get all users with activity in the period
        active_users = Task.objects.filter(
            completed_at__range=[start_date, end_date],
            is_completed=True
        ).values_list('user_id', flat=True).distinct()
        
        user_scores = {}
        
        for user_id in active_users:
            # Get tasks completed in period
            user_tasks = Task.objects.filter(
                user_id=user_id,
                completed_at__range=[start_date, end_date],
                is_completed=True
            )
            
            # Get XP earned in period
            xp_earned = XPLog.objects.filter(
                user_id=user_id,
                created_at__range=[start_date, end_date]
            ).aggregate(total=Sum('xp_earned'))['total'] or 0
            
            # Get user profile for streak info
            try:
                profile = ProgressProfile.objects.get(user_id=user_id)
                current_streak = profile.current_streak
                punctuality_rate = profile.punctuality_rate()
            except ProgressProfile.DoesNotExist:
                current_streak = 0
                punctuality_rate = 100
            
            # Calculate composite score
            tasks_completed = user_tasks.count()
            base_score = tasks_completed * 10 + xp_earned
            streak_bonus = current_streak * 5
            punctuality_bonus = int(punctuality_rate * 2)
            
            total_score = base_score + streak_bonus + punctuality_bonus
            
            user_scores[user_id] = {
                'total_score': total_score,
                'tasks_completed': tasks_completed,
                'total_xp': xp_earned,
                'current_streak': current_streak,
                'punctuality_rate': punctuality_rate
            }
        
        # Sort by total score
        return dict(sorted(user_scores.items(), key=lambda x: x[1]['total_score'], reverse=True))
    
    @staticmethod
    def get_user_rank(user_id: int, leaderboard_type: str = 'global') -> Optional[int]:
        """Get user's current rank in specified leaderboard"""
        try:
            entry = LeaderboardEntry.objects.filter(
                user_id=user_id,
                leaderboard_type__leaderboard_type=leaderboard_type
            ).order_by('-period_end').first()
            
            return entry.rank if entry else None
        except LeaderboardEntry.DoesNotExist:
            return None
    
    @staticmethod
    def get_leaderboard(leaderboard_type: str = 'global', limit: int = 10) -> List[Dict]:
        """Get top users from specified leaderboard"""
        entries = LeaderboardEntry.objects.filter(
            leaderboard_type__leaderboard_type=leaderboard_type
        ).select_related('user', 'leaderboard_type').order_by('rank')[:limit]
        
        return [
            {
                'rank': entry.rank,
                'user': entry.user,
                'score': entry.score,
                'tasks_completed': entry.tasks_completed,
                'total_xp': entry.total_xp,
                'streak_count': entry.streak_count,
                'punctuality_rate': entry.punctuality_rate
            }
            for entry in entries
        ]
    
    @staticmethod
    def get_user_position_context(user_id: int, leaderboard_type: str = 'global') -> Dict:
        """Get user's position with nearby users for context"""
        user_rank = LeaderboardService.get_user_rank(user_id, leaderboard_type)
        if not user_rank:
            return {'user_rank': None, 'context': []}
        
        # Get users above and below
        context_range = 5
        start_rank = max(1, user_rank - context_range)
        end_rank = user_rank + context_range
        
        entries = LeaderboardEntry.objects.filter(
            leaderboard_type__leaderboard_type=leaderboard_type,
            rank__range=[start_rank, end_rank]
        ).select_related('user').order_by('rank')
        
        context = [
            {
                'rank': entry.rank,
                'user': entry.user,
                'score': entry.score,
                'is_current_user': entry.user_id == user_id
            }
            for entry in entries
        ]
        
        return {'user_rank': user_rank, 'context': context}


class MissionService:
    """Service for managing missions and rewards"""
    
    @staticmethod
    def assign_daily_missions(user_id: int) -> List[UserMission]:
        """Assign daily missions to a user"""
        from .models import ProgressProfile
        
        try:
            profile = ProgressProfile.objects.get(user_id=user_id)
        except ProgressProfile.DoesNotExist:
            return []
        
        # Check if user already has missions for today
        today = timezone.now().date()
        existing_missions = UserMission.objects.filter(
            user_id=user_id,
            assigned_date=today,
            mission_type='daily'
        )
        
        if existing_missions.exists():
            return list(existing_missions)
        
        # Get available mission templates based on user level
        available_templates = MissionTemplate.objects.filter(
            is_active=True,
            min_level__lte=profile.level,
            max_level__gte=profile.level,
            mission_type='daily'
        )
        
        # Select random missions (typically 3-5 daily missions)
        mission_count = random.randint(3, 5)
        selected_templates = random.sample(
            list(available_templates), 
            min(mission_count, len(available_templates))
        )
        
        # Create user missions
        missions = []
        for template in selected_templates:
            mission = UserMission.objects.create(
                user_id=user_id,
                template=template,
                mission_type='daily',
                assigned_date=today,
                target_value=MissionService._calculate_target_value(template, profile),
                xp_reward=template.base_xp_reward,
                coin_reward=template.base_coin_reward
            )
            missions.append(mission)
        
        return missions
    
    @staticmethod
    def _calculate_target_value(template: MissionTemplate, profile) -> int:
        """Calculate target value based on template and user profile"""
        base_target = template.base_target_value
        
        # Adjust based on user level and performance
        level_multiplier = 1 + (profile.level - 1) * 0.1
        performance_multiplier = 1 + (profile.average_completion_rate() - 0.5)
        
        adjusted_target = int(base_target * level_multiplier * performance_multiplier)
        return max(1, adjusted_target)  # Ensure at least 1
    
    @staticmethod
    def update_mission_progress(user_id: int, mission_type: str, progress_value: int = 1) -> List[UserMission]:
        """Update progress for user's active missions"""
        active_missions = UserMission.objects.filter(
            user_id=user_id,
            is_completed=False,
            template__mission_type=mission_type
        )
        
        completed_missions = []
        
        for mission in active_missions:
            mission.current_progress = min(
                mission.current_progress + progress_value,
                mission.target_value
            )
            
            if mission.current_progress >= mission.target_value:
                mission.is_completed = True
                mission.completed_at = timezone.now()
                completed_missions.append(mission)
                
                # Award XP and coins - Fixed method call
                MissionService._award_mission_rewards(user_id, mission)
            
            mission.save()
        
        return completed_missions
    
    @staticmethod
    def _award_mission_rewards(user_id: int, mission: UserMission) -> None:
        """Award XP and coins for completed mission"""
        # Create XP log entry
        XPLog.objects.create(
            user_id=user_id,
            action='mission_complete',
            xp_earned=mission.xp_reward,
            description=f'Mission: {mission.template.name}'
        )
        
        # Update user profile
        try:
            profile = ProgressProfile.objects.get(user_id=user_id)
            profile.total_xp += mission.xp_reward
            profile.save()
            profile.update_level()
        except ProgressProfile.DoesNotExist:
            pass
    
    @staticmethod
    def get_user_missions(user_id: int, mission_type: str = None) -> List[UserMission]:
        """Get user's current missions"""
        queryset = UserMission.objects.filter(user_id=user_id).select_related('template')
        
        if mission_type:
            queryset = queryset.filter(mission_type=mission_type)
        
        return list(queryset.order_by('-assigned_date', 'is_completed'))


class SystemService:
    """Service for managing system settings and maintenance"""
    
    @staticmethod
    def get_setting(key: str, default=None):
        """Get system setting value"""
        try:
            setting = SystemSetting.objects.get(key=key)
            return setting.get_value()
        except SystemSetting.DoesNotExist:
            return default
    
    @staticmethod
    def set_setting(key: str, value, description: str = '') -> SystemSetting:
        """Set system setting value"""
        setting, created = SystemSetting.objects.update_or_create(
            key=key,
            defaults={
                'value': str(value),
                'description': description,
                'updated_at': timezone.now()
            }
        )
        return setting
    
    @staticmethod
    def run_daily_maintenance() -> Dict:
        """Run daily maintenance tasks"""
        results = {
            'leaderboards_updated': False,
            'missions_assigned': 0,
            'notifications_cleaned': 0,
            'achievements_checked': 0
        }
        
        try:
            # Update daily leaderboards
            LeaderboardService.update_rankings('daily')
            results['leaderboards_updated'] = True
            
            # Assign daily missions to active users
            active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(days=7)
            )
            
            for user in active_users:
                missions = MissionService.assign_daily_missions(user.id)
                results['missions_assigned'] += len(missions)
            
            # Clean old notifications (older than 30 days)
            old_notifications = Notification.objects.filter(
                created_at__lt=timezone.now() - timedelta(days=30)
            )
            deleted_count = old_notifications.count()
            old_notifications.delete()
            results['notifications_cleaned'] = deleted_count
            
            # Update system settings
            SystemService.set_setting('last_maintenance_run', timezone.now().isoformat())
            
        except Exception as e:
            results['error'] = str(e)
        
        return results