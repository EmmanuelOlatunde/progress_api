
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
        # If annotated value is available, use it
        if hasattr(obj, 'task_count'):
            return obj.task_count
        
        # Otherwise fallback
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
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated to create a task")
        validated_data['user'] = user
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
            user_achievement = UserAchievement.objects.filter(user=user, achievement=obj).first()
            return bool(user_achievement and user_achievement.unlocked_at is not None)
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
    
    def validate_friend_username(self, value):
        """Validate that the friend username exists"""
        if value:
            try:
                self._validated_friend = User.objects.get(username=value)
            except User.DoesNotExist:
                raise serializers.ValidationError('User not found')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        friend_username = validated_data.pop('friend_username', None)
        if friend_username:
            validated_data['friend'] = getattr(self, '_validated_friend', None)
        validated_data['user'] = user
        return super().create(validated_data)
    
    def validate(self, data):
        user = self.context['request'].user if self.context.get('request') else None
        friend = getattr(self, '_validated_friend', None)
        if user and friend and UserFriendship.objects.filter(user=user, friend=friend).exists():
            raise serializers.ValidationError({'friend_username': 'Already friends'})
        return data


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
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    template = MissionTemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=MissionTemplate.objects.all(), write_only=True, source='template'
    )
    progress_percentage = serializers.ReadOnlyField()
    time_remaining = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    difficulty_color = serializers.SerializerMethodField()
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    
    class Meta:
        model = UserMission
        fields = [
            'id', 'user', 'template','template_id', 'title', 'description', 'target_value',
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
            from math import ceil
            return max(0, ceil(time_remaining.total_seconds() / 86400))
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
