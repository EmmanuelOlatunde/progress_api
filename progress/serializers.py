
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, WeeklyReview, Category, XPLog, ProgressProfile, Achievement, UserAchievement        # gamification/serializers.py - Serializers for Leaderboards, Missions, and Notifications
from .models import (
    LeaderboardType, LeaderboardEntry, UserFriendship,
    MissionTemplate, UserMission,
    Notification, NotificationType, UserNotificationSettings, NotificationQueue
)




User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'color', 'xp_multiplier', 'task_count', 'created_at']

    def get_task_count(self, obj):
        user = self.context['request'].user if self.context.get('request') else None
        if user and user.is_authenticated:
            return obj.tasks.filter(user=user).count()
        return obj.tasks.count()

class WeeklyReviewSerializer(serializers.ModelSerializer):
    completion_rate = serializers.ReadOnlyField()
    punctuality_score = serializers.ReadOnlyField()
    performance_grade = serializers.ReadOnlyField()
    suggestions_list = serializers.SerializerMethodField()
    
    class Meta:
        model = WeeklyReview
        fields = [
            'id', 'week_start', 'week_end', 'total_tasks', 'total_xp',
            'early_completions', 'on_time_completions', 'late_completions',
            'performance_score', 'performance_grade', 'completion_rate',
            'punctuality_score', 'suggestions', 'suggestions_list',
            'category_breakdown', 'created_at'
        ]
    
    def get_suggestions_list(self, obj):
        return obj.suggestions.split('\n') if obj.suggestions else []

class TaskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    xp_value = serializers.SerializerMethodField()
    timing_info = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'difficulty', 'priority', 'is_completed', 'due_date',
            'completed_at', 'created_at', 'updated_at', 'timing_info', 'xp_value'
        ]
        read_only_fields = ['completed_at']
    
    def get_timing_info(self, obj):
        return obj.get_timing_info()
    
    def get_xp_value(self, obj):
        from .gamification import GamificationEngine
        engine = GamificationEngine(obj.user)
        return engine.calculate_task_xp(obj)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class XPLogSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = XPLog
        fields = [
            'id', 'action', 'action_display', 'xp_earned', 
            'task', 'task_title', 'description', 'created_at'
        ]

class ProgressProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    punctuality_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = ProgressProfile
        fields = [
            'id', 'username', 'total_xp', 'current_level', 'current_streak', 
            'longest_streak', 'last_activity_date',
            'total_early_completions', 'total_on_time_completions',
            'total_late_completions', 'punctuality_rate',
            'xp_progress_in_current_level', 'xp_needed_for_next_level', 
            'progress_percentage'
        ]

class AchievementSerializer(serializers.ModelSerializer):
    is_unlocked = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()
    achievement_type_display = serializers.CharField(source='get_achievement_type_display', read_only=True)

    class Meta:
        model = Achievement
        fields = [
            'id', 'name', 'description', 'achievement_type', 'icon', 
            'threshold', 'xp_reward','achievement_type_display', 
            'is_unlocked', 'progress', 'unlocked_at'
        ]

    def get_is_unlocked(self, obj):
        user = self.context['request'].user if self.context.get('request') else None
        if user and user.is_authenticated:
            return UserAchievement.objects.filter(user=user, achievement=obj).exists()
        return False

    def get_progress(self, obj):
        user = self.context['request'].user if self.context.get('request') else None
        if user and user.is_authenticated:
            user_achievement = UserAchievement.objects.filter(user=user, achievement=obj).first()
            if user_achievement:
                return user_achievement.progress
            
            # Calculate current progress for unachieved achievements
            from .gamification import GamificationEngine
            engine = GamificationEngine(user)
            return engine.get_achievement_progress(obj)
        return 0

    def get_unlocked_at(self, obj):
        user = self.context['request'].user if self.context.get('request') else None
        if user and user.is_authenticated:
            user_achievement = UserAchievement.objects.filter(user=user, achievement=obj).first()
            return user_achievement.unlocked_at if user_achievement else None
        return None
    
class UserAchievementSerializer(serializers.ModelSerializer):

    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'progress', 'unlocked_at']

# ============ USER SERIALIZERS ============

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for leaderboards and public displays"""
    avatar_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'avatar_url']
    
    def get_avatar_url(self, obj):
        return obj.get_avatar_url()
    
    def get_display_name(self, obj):
        return obj.display_name

# ============ LEADERBOARD SERIALIZERS ============

class LeaderboardTypeSerializer(serializers.ModelSerializer):
    """Leaderboard type serializer"""
    
    class Meta:
        model = LeaderboardType
        fields = [
            'id', 'name', 'leaderboard_type', 'description', 
            'is_active', 'reset_frequency', 'category', 'created_at'
        ]

class LeaderboardEntrySerializer(serializers.ModelSerializer):
    """Leaderboard entry serializer"""
    user = UserBasicSerializer(read_only=True)
    leaderboard_type = LeaderboardTypeSerializer(read_only=True)
    rank_change = serializers.SerializerMethodField()
    performance_badge = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaderboardEntry
        fields = [
            'id', 'user', 'leaderboard_type', 'score', 'rank',
            'tasks_completed', 'total_xp', 'streak_count', 'punctuality_rate',
            'period_start', 'period_end', 'rank_change', 'performance_badge',
            'created_at', 'updated_at'
        ]
    
    def get_rank_change(self, obj):
        """Calculate rank change from previous period"""
        # This would require historical data - simplified for now
        return 0
    
    def get_performance_badge(self, obj):
        """Get performance badge based on stats"""
        if obj.punctuality_rate >= 90:
            return {'name': 'Time Master', 'color': '#gold'}
        elif obj.streak_count >= 7:
            return {'name': 'Streak Legend', 'color': '#orange'}
        elif obj.tasks_completed >= 50:
            return {'name': 'Task Crusher', 'color': '#blue'}
        return None

class UserFriendshipSerializer(serializers.ModelSerializer):
    """User friendship serializer"""
    friend = UserBasicSerializer(read_only=True)
    friend_username = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = UserFriendship
        fields = ['id', 'friend', 'friend_username', 'status', 'created_at']
    
    def create(self, validated_data):
        friend_username = validated_data.pop('friend_username', None)
        if friend_username:
            try:
                friend = User.objects.get(username=friend_username)
                validated_data['friend'] = friend
            except User.DoesNotExist:
                raise serializers.ValidationError({'friend_username': 'User not found'})
        
        return super().create(validated_data)

# ============ MISSION SERIALIZERS ============

class MissionTemplateSerializer(serializers.ModelSerializer):
    """Mission template serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    estimated_time = serializers.SerializerMethodField()
    
    class Meta:
        model = MissionTemplate
        fields = [
            'id', 'name', 'description', 'mission_type', 'difficulty',
            'target_value', 'duration_days', 'xp_reward', 'bonus_multiplier',
            'category', 'category_name', 'min_user_level', 'max_user_level',
            'is_repeatable', 'estimated_time'
        ]
    
    def get_estimated_time(self, obj):
        """Estimate time to complete mission based on type and difficulty"""
        base_times = {
            'easy': 2,
            'medium': 5,
            'hard': 10,
            'legendary': 20
        }
        return base_times.get(obj.difficulty, 5)

class UserMissionSerializer(serializers.ModelSerializer):
    """User mission serializer"""
    template = MissionTemplateSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    time_remaining = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    difficulty_color = serializers.SerializerMethodField()
    
    class Meta:
        model = UserMission
        fields = [
            'id', 'template', 'title', 'description', 'target_value',
            'current_progress', 'progress_percentage', 'start_date', 'end_date',
            'completed_at', 'status', 'status_display', 'xp_reward',
            'bonus_multiplier', 'category', 'time_remaining', 'is_expired',
            'days_remaining', 'difficulty_color', 'created_at', 'updated_at'
        ]
    
    def get_days_remaining(self, obj):
        """Get days remaining for mission"""
        if obj.status != 'active':
            return 0
        
        time_remaining = obj.time_remaining
        if time_remaining:
            return max(0, time_remaining.days)
        return 0
    
    def get_difficulty_color(self, obj):
        """Get color based on difficulty"""
        colors = {
            'easy': '#28a745',
            'medium': '#ffc107',
            'hard': '#fd7e14',
            'legendary': '#dc3545'
        }
        return colors.get(obj.template.difficulty if obj.template else 'medium', '#ffc107')

class MissionProgressSerializer(serializers.Serializer):
    """Mission progress update serializer"""
    mission_id = serializers.IntegerField()
    progress_increment = serializers.IntegerField(default=1)
    task_id = serializers.IntegerField(required=False)

# ============ NOTIFICATION SERIALIZERS ============

class NotificationTypeSerializer(serializers.ModelSerializer):
    """Notification type serializer"""
    
    class Meta:
        model = NotificationType
        fields = [
            'id', 'name', 'display_name', 'description', 
            'default_enabled', 'can_disable', 'icon', 'color'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer"""
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    notification_icon = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'priority',
            'priority_display', 'is_read', 'is_archived', 'data',
            'action_url', 'action_text', 'created_at', 'read_at',
            'expires_at', 'time_ago', 'is_expired', 'notification_icon'
        ]
    
    def get_time_ago(self, obj):
        """Get human-readable time ago"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)
    
    def get_notification_icon(self, obj):
        """Get icon based on notification type"""
        icons = {
            'task_reminder': '📋',
            'mission_completed': '🎯',
            'mission_failed': '❌',
            'achievement_unlocked': '🏆',
            'friend_request': '👥',
            'leaderboard_update': '📊',
            'level_up': '⬆️',
            'streak_milestone': '🔥',
            'weekly_review': '📈',
            'system_update': '🔔',
        }
        return icons.get(obj.notification_type, '📢')

class UserNotificationSettingsSerializer(serializers.ModelSerializer):
    """User notification settings serializer"""
    
    class Meta:
        model = UserNotificationSettings
        fields = [
            'email_notifications', 'email_task_reminders', 'email_mission_updates',
            'email_achievement_unlocks', 'email_leaderboard_updates', 'email_weekly_summary',
            'push_notifications', 'push_task_reminders', 'push_mission_updates',
            'push_achievement_unlocks', 'push_leaderboard_updates',
            'reminder_frequency', 'quiet_hours_start', 'quiet_hours_end'
        ]

class NotificationQueueSerializer(serializers.ModelSerializer):
    """Notification queue serializer"""
    user = UserBasicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = NotificationQueue
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'scheduled_for', 'status', 'status_display', 'send_email',
            'send_push', 'attempts', 'max_attempts', 'error_message',
            'created_at', 'processed_at'
        ]

# ============ DASHBOARD SERIALIZERS ============

class GameDashboardSerializer(serializers.Serializer):
    """Gamification dashboard summary serializer"""
    user_level = serializers.IntegerField()
    user_xp = serializers.IntegerField()
    user_rank = serializers.IntegerField(allow_null=True)
    active_missions_count = serializers.IntegerField()
    unread_notifications_count = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    weekly_tasks_completed = serializers.IntegerField()
    recent_achievements = serializers.ListField()
    
class LeaderboardSummarySerializer(serializers.Serializer):
    """Leaderboard summary for dashboard"""
    global_rank = serializers.IntegerField(allow_null=True)
    category_ranks = serializers.DictField()
    friends_rank = serializers.IntegerField(allow_null=True)
    total_participants = serializers.IntegerField()
    rank_change = serializers.IntegerField()

class MissionSummarySerializer(serializers.Serializer):
    """Mission summary for dashboard"""
    active_missions = UserMissionSerializer(many=True)
    completed_this_week = serializers.IntegerField()
    available_missions_count = serializers.IntegerField()
    success_rate = serializers.FloatField()

# ============ BULK OPERATION SERIALIZERS ============

class BulkNotificationSerializer(serializers.Serializer):
    """Bulk notification operations"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['mark_read', 'archive', 'delete'])

class BulkMissionSerializer(serializers.Serializer):
    """Bulk mission operations"""
    mission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['abandon', 'refresh_progress'])

# ============ STATISTICS SERIALIZERS ============

class UserStatsSerializer(serializers.Serializer):
    """User statistics serializer"""
    total_missions_completed = serializers.IntegerField()
    total_missions_failed = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_completion_time = serializers.FloatField()
    favorite_mission_type = serializers.CharField()
    total_friends = serializers.IntegerField()
    global_rank = serializers.IntegerField(allow_null=True)
    badges_earned = serializers.ListField()

class SystemStatsSerializer(serializers.Serializer):
    """System-wide statistics serializer"""
    total_users = serializers.IntegerField()
    active_missions = serializers.IntegerField()
    completed_missions = serializers.IntegerField()
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    active_friendships = serializers.IntegerField()
    pending_friend_requests = serializers.IntegerField()
    popular_mission_types = serializers.DictField()
    average_user_level = serializers.FloatField()