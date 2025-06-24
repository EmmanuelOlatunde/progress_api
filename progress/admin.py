from django.contrib import admin
from .models import Category, Task, XPLog, ProgressProfile, Achievement, UserAchievement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'xp_multiplier', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'difficulty', 'priority', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'difficulty', 'priority', 'category', 'created_at']
    search_fields = ['title', 'user__username']
    date_hierarchy = 'created_at'

@admin.register(XPLog)
class XPLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'xp_earned', 'task', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'description']
    date_hierarchy = 'created_at'

@admin.register(ProgressProfile)
class ProgressProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_level', 'total_xp', 'current_streak', 'longest_streak']
    list_filter = ['current_level', 'created_at']
    search_fields = ['user__username']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'achievement_type', 'threshold', 'xp_reward', 'is_hidden']
    list_filter = ['achievement_type', 'is_hidden']

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'progress', 'unlocked_at']
    list_filter = ['achievement__achievement_type', 'unlocked_at']
    search_fields = ['user__username', 'achievement__name']