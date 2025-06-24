from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Existing ViewSets
    TaskViewSet, CategoryViewSet, XPViewSet, AchievementViewSet, StatsViewSet, 
    WeeklyReviewViewSet, UserProgressProfileViewSet,
    # New ViewSets from paste.txt
    LeaderboardViewSet, FriendshipViewSet, MissionViewSet, NotificationViewSet,
    NotificationSettingsViewSet, GameStatsViewSet,
    # Views
    index
)

# Create router and register all ViewSets
router = DefaultRouter()

# Original ViewSets
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'xp', XPViewSet, basename='xp')
router.register(r'achievements', AchievementViewSet, basename='achievement')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'weekly-reviews', WeeklyReviewViewSet, basename='weeklyreview')
router.register(r'user-progress', UserProgressProfileViewSet, basename='userprogress')

# New ViewSets from gamification system
router.register(r'leaderboard', LeaderboardViewSet, basename='leaderboard')
router.register(r'friendships', FriendshipViewSet, basename='friendship')
router.register(r'missions', MissionViewSet, basename='mission')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'notification-settings', NotificationSettingsViewSet, basename='notification-settings')
router.register(r'game-stats', GameStatsViewSet, basename='game-stats')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Direct paths
    path('', include(router.urls)),
    path('index/', index, name='index'),
]