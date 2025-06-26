from django.contrib import admin
from .models import (
    MissionTemplate, UserMission, LeaderboardType, LeaderboardEntry,
    UserFriendship, Notification, NotificationType, UserNotificationSettings,
    NotificationQueue, SystemSetting, Category, Task, XPLog, ProgressProfile, 
    Achievement, UserAchievement, WeeklyReview
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'xp_multiplier', 'created_at']
    list_filter = ['created_at', 'xp_multiplier']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'difficulty', 'priority', 'is_completed', 'due_date', 'created_at']
    list_filter = ['is_completed', 'difficulty', 'priority', 'category', 'created_at', 'due_date']
    search_fields = ['title', 'description', 'user__username']
    ordering = ['-created_at']

@admin.register(XPLog)
class XPLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'xp_earned', 'task', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'description', 'task__title']
    ordering = ['-created_at']

@admin.register(ProgressProfile)
class ProgressProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_level', 'total_xp', 'current_streak', 'last_activity_date']
    list_filter = ['current_level', 'last_activity_date', 'created_at']
    search_fields = ['user__username']
    ordering = ['-total_xp']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'achievement_type', 'icon', 'threshold', 'xp_reward', 'is_hidden']
    list_filter = ['achievement_type', 'is_hidden', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['achievement_type', 'threshold']

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'progress', 'unlocked_at']
    list_filter = ['achievement__achievement_type', 'unlocked_at']
    search_fields = ['user__username', 'achievement__name']
    ordering = ['-unlocked_at']

@admin.register(WeeklyReview)
class WeeklyReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'week_start', 'week_end', 'performance_score', 'total_tasks', 'total_xp', 'created_at']
    list_filter = ['week_start', 'performance_score', 'created_at']
    search_fields = ['user__username']
    ordering = ['-week_start']

@admin.register(MissionTemplate)
class MissionTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'mission_type', 'difficulty', 'target_value', 'duration_days', 'xp_reward', 'is_active']
    list_filter = ['mission_type', 'difficulty', 'is_active', 'is_repeatable', 'category', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['difficulty', 'name']

@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status', 'current_progress', 'target_value', 'end_date', 'xp_reward']
    list_filter = ['status', 'template__difficulty', 'template__mission_type', 'category', 'start_date', 'end_date']
    search_fields = ['user__username', 'title', 'description']
    ordering = ['-created_at']

@admin.register(LeaderboardType)
class LeaderboardTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'leaderboard_type', 'is_active', 'reset_frequency', 'category']
    list_filter = ['leaderboard_type', 'is_active', 'reset_frequency', 'category']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'leaderboard_type', 'rank', 'score', 'tasks_completed', 'total_xp', 'streak_count']
    list_filter = ['leaderboard_type', 'period_start', 'period_end']
    search_fields = ['user__username', 'leaderboard_type__name']
    ordering = ['leaderboard_type', 'rank']

@admin.register(UserFriendship)
class UserFriendshipAdmin(admin.ModelAdmin):
    list_display = ['user', 'friend', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'friend__username']
    ordering = ['-created_at']

@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'default_enabled', 'can_disable', 'icon', 'color']
    list_filter = ['default_enabled', 'can_disable']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['display_name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'priority', 'is_read', 'is_archived', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'is_archived', 'created_at', 'expires_at']
    search_fields = ['user__username', 'title', 'message']
    ordering = ['-created_at']

@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'push_notifications', 'reminder_frequency']
    list_filter = ['email_notifications', 'push_notifications', 'reminder_frequency']
    search_fields = ['user__username']
    ordering = ['user__username']

@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'status', 'scheduled_for', 'attempts']
    list_filter = ['status', 'notification_type', 'send_email', 'send_push', 'scheduled_for', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    ordering = ['scheduled_for']

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', 'updated_at']
    list_filter = [ 'updated_at']
    search_fields = ['key', 'description']
    ordering = ['key']