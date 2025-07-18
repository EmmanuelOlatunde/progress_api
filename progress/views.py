# progress/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db import models
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q 
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from datetime import datetime, timedelta
from django_filters.rest_framework import DjangoFilterBackend
from .filters import TaskFilter 
from .gamification import GamificationEngine
from rest_framework.pagination import PageNumberPagination
import random
from rest_framework.exceptions import NotFound
from .pagination import CustomPageNumberPagination
import logging
from .models import (
    Task, Category, XPLog, ProgressProfile, Achievement,
    LeaderboardType, LeaderboardEntry, UserFriendship,
    MissionTemplate, UserMission, WeeklyReview, UserAchievement, 
    Notification, NotificationType, UserNotificationSettings)
from .serializers import (
    LeaderboardTypeSerializer, LeaderboardEntrySerializer, UserFriendshipSerializer,
    MissionTemplateSerializer, UserMissionSerializer,
    NotificationSerializer, NotificationTypeSerializer, UserNotificationSettingsSerializer,
    TaskSerializer, CategorySerializer, XPLogSerializer, 
    ProgressProfileSerializer, AchievementSerializer, WeeklyReviewSerializer)


logger = logging.getLogger(__name__)
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return Category.objects.annotate(
            task_count=Count('tasks', filter=Q(tasks__user=self.request.user))
        ).order_by('created_at')

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskFilter

    def get_queryset(self):
        """Get tasks for the current user"""
        # Handle schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Task.objects.none()
        
        # Your existing logic here
        queryset = Task.objects.filter(user=self.request.user)
        if not queryset.exists():
            # Instead of raising NotFound, return empty queryset
            return Task.objects.none()
        return queryset

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        """Mark task as completed and award XP"""
        task = self.get_object()

        if task.is_completed:
            return Response(
                {'error': 'Task is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, message = task.complete_task()

        if success:
            # profile = ProgressProfile.objects.get(user=request.user) # Uncomment if ProgressProfile is defined
            return Response({
                'message': message,
                'task': TaskSerializer(task).data
            })

        return Response(
            {'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get task statistics"""
        user_tasks = Task.objects.filter(user=request.user)

        total_tasks = user_tasks.count()
        completed_tasks = user_tasks.filter(is_completed=True).count()
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Category breakdown
        category_stats = {}
        for category in Category.objects.all():
            cat_tasks = user_tasks.filter(category=category)
            cat_completed = cat_tasks.filter(is_completed=True).count()
            category_stats[category.name] = {
                'total': cat_tasks.count(),
                'completed': cat_completed,
                'completion_rate': (cat_completed / cat_tasks.count() * 100) if cat_tasks.count() > 0 else 0
            }

        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_completed = user_tasks.filter(
            is_completed=True,
            completed_at__gte=week_ago
        ).count()

        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': total_tasks - completed_tasks,
            'completion_rate': round(completion_rate, 2),
            'recent_completed': recent_completed,
            'category_breakdown': category_stats
        })

class XPViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = XPLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return XPLog.object()
        return XPLog.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get XP summary and level information"""
        profile, created = ProgressProfile.objects.get_or_create(user=request.user)
        serializer = ProgressProfileSerializer(profile)
        
        # Recent XP activity
        recent_xp = XPLog.objects.filter(
            user=request.user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:10]
        
        return Response({
            'profile': serializer.data,
            'recent_activity': XPLogSerializer(recent_xp, many=True).data
        })

    @action(detail=False, methods=['get'])
    def level(self, request):
        """Get detailed level information"""
        profile, created = ProgressProfile.objects.get_or_create(user=request.user)
        
        return Response({
            'current_level': profile.current_level,
            'total_xp': profile.total_xp,
            'xp_for_current_level': profile.calculate_xp_for_level(profile.current_level),
            'xp_for_next_level': profile.xp_for_next_level,
            'xp_progress_in_level': profile.xp_progress_in_current_level,
            'xp_needed_for_next': profile.xp_needed_for_next_level,
            'progress_percentage': min(100, (profile.xp_progress_in_current_level / max(1, profile.xp_for_next_level - profile.calculate_xp_for_level(profile.current_level))) * 100)
        })

class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Show all achievements, including locked ones
        return Achievement.objects.all().order_by('-is_hidden', 'achievement_type', 'threshold')

    @action(detail=False, methods=['get'])
    def unlocked(self, request):
        """Get only unlocked achievements"""
        unlocked_achievements = UserAchievement.objects.filter(
            user=request.user
        ).select_related('achievement').order_by('-unlocked_at')
        
        return Response([
            {
                **AchievementSerializer(ua.achievement, context={'request': request}).data,
                'unlocked_at': ua.unlocked_at
            }
            for ua in unlocked_achievements
        ])

class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Comprehensive statistics dashboard"""
        user = request.user
        profile, created = ProgressProfile.objects.get_or_create(user=user)
        
        # Initialize gamification engine
        engine = GamificationEngine(user)
        
        # ADDED: Debug current streak status if needed
        if request.GET.get('debug') == 'true':
            debug_info = engine.debug_streak_status()
            print("DEBUG INFO:", debug_info)
        
        # ADDED: Option to recalculate streak if it seems wrong
        if request.GET.get('recalculate_streak') == 'true':
            engine.recalculate_streak()
            # Refresh profile from database
            profile.refresh_from_db()
        
        # Task statistics
        tasks = Task.objects.filter(user=user)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(is_completed=True).count()
        
        # XP statistics
        total_xp = profile.total_xp
        current_level = profile.current_level
        
        # Achievement statistics
        total_achievements = Achievement.objects.count()
        unlocked_achievements = UserAchievement.objects.filter(user=user).count()
        
        # Category breakdown with XP
        category_stats = []
        for category in Category.objects.all():
            cat_tasks = tasks.filter(category=category)
            cat_completed = cat_tasks.filter(is_completed=True)
            
            # FIXED: Calculate XP from actual XP logs instead of recalculating
            cat_xp = XPLog.objects.filter(
                user=user,
                task__category=category,
                action='task_complete'
            ).aggregate(total=models.Sum('xp_earned'))['total'] or 0
            
            category_stats.append({
                'name': category.name,
                'color': category.color,
                'total_tasks': cat_tasks.count(),
                'completed_tasks': cat_completed.count(),
                'total_xp': cat_xp
            })

        # ADDED: Recent activity to help debug streak issues
        recent_activity = self._get_recent_activity(user)

        return Response({
            'profile': {
                'username': user.username,
                'level': current_level,
                'total_xp': total_xp,
                'current_streak': profile.current_streak,
                'longest_streak': profile.longest_streak,
                'last_activity_date': profile.last_activity_date
            },
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            'achievement_stats': {
                'unlocked': unlocked_achievements,
                'total': total_achievements,
                'completion_rate': (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
            },
            'category_breakdown': category_stats,
            'recent_activity': recent_activity  # ADDED for debugging
        })

    def _get_recent_activity(self, user):
        """Get recent activity for debugging streak issues"""
        today = timezone.now().date()
        recent_days = []
        
        for i in range(7):  # Last 7 days
            date = today - timedelta(days=i)
            completed_count = Task.objects.filter(
                user=user,
                is_completed=True,
                completed_at__date=date
            ).count()
            
            recent_days.append({
                'date': date.isoformat(),
                'completed_tasks': completed_count,
                'has_activity': completed_count > 0
            })
        
        return recent_days

    @action(detail=False, methods=['get'])
    def streaks(self, request):
        """Get streak information with proper updates"""
        user = request.user
        profile, created = ProgressProfile.objects.get_or_create(user=user)
        engine = GamificationEngine(user)
        
        # ADDED: Force streak recalculation if requested
        if request.GET.get('force_update') == 'true':
            engine.recalculate_streak()
            profile.refresh_from_db()
        
        # Calculate streak data for last 30 days
        today = timezone.now().date()
        streak_data = []
        
        for i in range(30):
            date = today - timedelta(days=i)
            completed_tasks = Task.objects.filter(
                user=request.user,
                is_completed=True,
                completed_at__date=date
            ).count()
            
            streak_data.append({
                'date': date.isoformat(),
                'tasks_completed': completed_tasks,
                'has_activity': completed_tasks > 0
            })
        
        # ADDED: Calculate what the streak SHOULD be based on recent activity
        calculated_streak = self._calculate_current_streak_from_data(reversed(streak_data))
        
        response_data = {
            'current_streak': profile.current_streak,
            'longest_streak': profile.longest_streak,
            'last_activity': profile.last_activity_date,
            'daily_activity': list(reversed(streak_data)),  # Most recent first
            'calculated_streak': calculated_streak,  # ADDED for comparison
            'streak_matches': profile.current_streak == calculated_streak  # ADDED for debugging
        }
        
        # ADDED: Auto-fix if streak doesn't match calculated value
        if not response_data['streak_matches'] and calculated_streak > 0:
            print(f"WARNING: Streak mismatch. DB says {profile.current_streak}, calculated {calculated_streak}")
            if request.GET.get('auto_fix') == 'true':
                engine.recalculate_streak()
                profile.refresh_from_db()
                response_data['current_streak'] = profile.current_streak
                response_data['streak_matches'] = True
                response_data['auto_fixed'] = True
        
        return Response(response_data)
    
    def _calculate_current_streak_from_data(self, daily_activity):
        """Calculate what the current streak should be based on activity data"""
        current_streak = 0
        
        for day in daily_activity:  # Should be ordered from oldest to newest
            if day['has_activity']:
                current_streak += 1
            else:
                current_streak = 0  # Reset streak on inactive day
        
        return current_streak

    @action(detail=False, methods=['post'])
    def debug_streak(self, request):
        """Debug endpoint to analyze streak issues"""
        user = request.user
        engine = GamificationEngine(user)
        
        debug_info = engine.debug_streak_status()
        
        return Response({
            'debug_info': debug_info,
            'actions_available': {
                'recalculate': 'POST to /api/stats/fix_streak/',
                'view_with_debug': 'GET /api/stats/?debug=true',
                'force_streak_update': 'GET /api/stats/streaks/?force_update=true'
            }
        })
    
    @action(detail=False, methods=['post'])
    def fix_streak(self, request):
        """Fix streak calculation issues"""
        user = request.user
        engine = GamificationEngine(user)
        
        old_streak = engine.profile.current_streak
        old_longest = engine.profile.longest_streak
        
        result = engine.recalculate_streak()
        if result is None:
            return Response({
                'message': 'Streak recalculation failed unexpectedly.',
                'reason': 'GamificationEngine.recalculate_streak() returned None'
            }, status=500)

        return Response({
            'message': 'Streak recalculated successfully',
            'old_values': {
                'current_streak': old_streak,
                'longest_streak': old_longest
            },
            'new_values': result,
            'changed': {
                'current_streak': result['current_streak'] != old_streak,
                'longest_streak': result['longest_streak'] != old_longest
            }
        })

    @action(detail=False, methods=['get']) 
    def xp_breakdown(self, request):
        """Get detailed XP breakdown"""
        user = request.user
        
        # XP by action type
        xp_by_action = XPLog.objects.filter(user=user).values('action').annotate(
            total_xp=models.Sum('xp_earned'),
            count=models.Count('id')
        )
        
        # Recent XP activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_xp = XPLog.objects.filter(
            user=user,
            created_at__gte=week_ago
        ).order_by('-created_at')
        
        recent_activity = [{
            'date': log.created_at.date().isoformat(),
            'action': log.action,
            'xp_earned': log.xp_earned,
            'description': log.description,
            'task_title': log.task.title if log.task else None
        } for log in recent_xp]
        
        return Response({
            'xp_by_action': list(xp_by_action),
            'recent_activity': recent_activity,
            'total_xp': sum(item['total_xp'] for item in xp_by_action)
        })
    
class WeeklyReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing WeeklyReview instances.
    Provides CRUD operations plus additional endpoints for analytics.
    """
    serializer_class = WeeklyReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
            """Get weekly reviews for the current user"""
            # Handle schema generation
            if getattr(self, 'swagger_fake_view', False):
                return WeeklyReview.objects.none()
            
            # Your existing logic here
            queryset = WeeklyReview.objects.filter(user=self.request.user)
            if not queryset.exists():
                # Instead of raising NotFound, return empty queryset
                return WeeklyReview.objects.none()
            return queryset
    
    def perform_create(self, serializer):
        """Automatically set the user when creating a review"""
        serializer.save(user=self.request.user)
    
    def get_object(self):
        """Ensure users can only access their own reviews"""
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj
    
    @action(detail=False, methods=['get'])
    def current_week(self, request):
        """Get or create the current week's review"""
        today = timezone.now().date()
        # Calculate start of current week (Monday)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        try:
            review = WeeklyReview.objects.get(
                user=request.user,
                week_start=week_start
            )
        except WeeklyReview.DoesNotExist:
            # Create a new review for current week
            review = WeeklyReview.objects.create(
                user=request.user,
                week_start=week_start,
                week_end=week_end
            )
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def date_range(self, request):
        """Get reviews within a specific date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Both start_date and end_date parameters are required (YYYY-MM-DD format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reviews = self.get_queryset().filter(
            week_start__gte=start_date,
            week_end__lte=end_date
        )
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """Get performance summary statistics"""
        reviews = self.get_queryset()
        
        if not reviews.exists():
            return Response({
                'message': 'No reviews found',
                'summary': {}
            })
        
        # Calculate summary statistics
        total_weeks = reviews.count()
        avg_performance = reviews.aggregate(
            avg_score=models.Avg('performance_score'),
            avg_completion_rate=models.Avg('total_tasks'),
            total_xp=models.Sum('total_xp')
        )
        
        # Get grade distribution
        grade_counts = {}
        for review in reviews:
            grade = review.performance_grade
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Get recent trend (last 4 weeks)
        recent_reviews = reviews[:4]
        recent_scores = [r.performance_score for r in recent_reviews]
        
        trend = 'stable'
        if len(recent_scores) >= 2:
            if recent_scores[0] > recent_scores[-1] + 5:
                trend = 'improving'
            elif recent_scores[0] < recent_scores[-1] - 5:
                trend = 'declining'
        
        summary = {
            'total_weeks_reviewed': total_weeks,
            'average_performance_score': round(avg_performance['avg_score'] or 0, 1),
            'total_xp_earned': avg_performance['total_xp'] or 0,
            'grade_distribution': grade_counts,
            'recent_trend': trend,
            'recent_scores': recent_scores
        }
        
        return Response({'summary': summary})
    
    @action(detail=False, methods=['get'])
    def top_categories(self, request):
        """Get top performing categories across all reviews"""
        reviews = self.get_queryset().exclude(category_breakdown={})
        
        category_stats = {}
        for review in reviews:
            for category, data in review.category_breakdown.items():
                if category not in category_stats:
                    category_stats[category] = {
                        'total_tasks': 0,
                        'total_xp': 0,
                        'weeks_active': 0
                    }
                
                category_stats[category]['total_tasks'] += data.get('tasks', 0)
                category_stats[category]['total_xp'] += data.get('xp', 0)
                category_stats[category]['weeks_active'] += 1
        
        # Sort by total XP
        sorted_categories = sorted(
            category_stats.items(),
            key=lambda x: x[1]['total_xp'],
            reverse=True
        )
        
        return Response({
            'top_categories': dict(sorted_categories[:10])  # Top 10
        })
    
    @action(detail=True, methods=['patch'])
    def add_suggestion(self, request, pk=None):
        """Add a suggestion to an existing review"""
        review = self.get_object()
        new_suggestion = request.data.get('suggestion', '').strip()
        
        if not new_suggestion:
            return Response(
                {'error': 'Suggestion text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if review.suggestions:
            review.suggestions += f"\n{new_suggestion}"
        else:
            review.suggestions = new_suggestion
        
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """Override list to add filtering options"""
        queryset = self.get_queryset()
        
        # Filter by performance grade
        grade = request.query_params.get('grade')
        if grade:
            # Filter by calculated grade (this requires evaluation)
            filtered_reviews = [r for r in queryset if r.performance_grade == grade.upper()]
            queryset = WeeklyReview.objects.filter(
                id__in=[r.id for r in filtered_reviews]
            ).order_by('-week_start')
        
        # Filter by minimum performance score
        min_score = request.query_params.get('min_score')
        if min_score:
            try:
                min_score = int(min_score)
                queryset = queryset.filter(performance_score__gte=min_score)
            except ValueError:
                pass
        
        # Filter by year
        year = request.query_params.get('year')
        if year:
            try:
                year = int(year)
                queryset = queryset.filter(week_start__year=year)
            except ValueError:
                pass
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class UserProgressProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows authenticated users to retrieve their own ProgressProfile,
    or potentially list a queryset filtered to their own profiles.
    """
    serializer_class = ProgressProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns only the ProgressProfile for the currently authenticated user.
        This handles both list and retrieve actions for the current user.
        """
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Profile found.")
        return ProgressProfile.objects.filter(user=self.request.user).order_by('id')

    def get_object(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Profile found.")
        return self.request.user.progress_profile
    
# ============ LEADERBOARD VIEWS ============

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """Leaderboard API endpoints"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = LeaderboardEntrySerializer
    queryset = LeaderboardEntry.objects.all()
    
    def get_queryset(self):
        """Override get_queryset to handle schema generation gracefully"""
        # Check if this is a schema generation request
        if getattr(self, 'swagger_fake_view', False):
            return LeaderboardEntry.objects.none()
        
        # Default queryset for list/retrieve actions
        return LeaderboardEntry.objects.select_related('user', 'leaderboard_type').order_by('-score')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'types':
            return LeaderboardTypeSerializer
        return LeaderboardEntrySerializer
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available leaderboard types"""
        types = LeaderboardType.objects.filter(is_active=True)
        serializer = LeaderboardTypeSerializer(types, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def global_leaderboard(self, request):
        """Get global leaderboard"""
        period = request.query_params.get('period', 'all_time')
        category_id = request.query_params.get('category')
        
        # Calculate date range based on period
        end_date = timezone.now()
        if period == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = timezone.make_aware(datetime(2020, 1, 1))
        
        # Get leaderboard entries
        queryset = LeaderboardEntry.objects.filter(
            period_start__gte=start_date,
            period_end__lte=end_date
        )
        
        if category_id:
            queryset = queryset.filter(leaderboard_type__category_id=category_id)
        
        # Get top entries with user details
        entries = queryset.select_related('user', 'leaderboard_type').order_by('-score')[:50]
        
        # Get current user's position
        user_entry = queryset.filter(user=request.user).first()
        user_rank = None
        if user_entry:
            user_rank = queryset.filter(score__gt=user_entry.score).count() + 1
        
        serializer = LeaderboardEntrySerializer(entries, many=True)
        return Response({
            'entries': serializer.data,
            'user_rank': user_rank,
            'total_participants': queryset.values('user').distinct().count(),
            'period': period
        })
    
    @action(detail=False, methods=['get'])
    def friends_leaderboard(self, request):
        """Get friends-only leaderboard"""
        # Get user's friends
        friends = UserFriendship.objects.filter(
            user=request.user,
            status='accepted'
        ).values_list('friend_id', flat=True)
        
        # Include current user
        user_ids = list(friends) + [request.user.id]
        
        # Get recent entries for friends
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)  # Last 30 days
        
        entries = LeaderboardEntry.objects.filter(
            user_id__in=user_ids,
            period_start__gte=start_date
        ).select_related('user').order_by('-score')
        
        serializer = LeaderboardEntrySerializer(entries, many=True)
        return Response({
            'entries': serializer.data,
            'friends_count': len(friends)
        })
    
    @action(detail=False, methods=['get'])
    def category_rankings(self, request):
        """Get leaderboard rankings by category"""
        from .models import Category
        
        categories = Category.objects.all()
        rankings = []
        
        for category in categories:
            entries = LeaderboardEntry.objects.filter(
                leaderboard_type__category=category
            ).select_related('user').order_by('-score')[:10]
            
            rankings.append({
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'color': category.color
                },
                'top_users': LeaderboardEntrySerializer(entries, many=True).data
            })
        
        return Response({'category_rankings': rankings})
    
    @action(detail=False, methods=['post'])
    def refresh_rankings(self, request):
        """Manually refresh leaderboard rankings"""
        from .gamification import LeaderboardService
        
        period = request.data.get('period', 'weekly')
        LeaderboardService.update_rankings(period)
        
        return Response({'message': 'Rankings updated successfully'})

class FriendshipViewSet(viewsets.ReadOnlyModelViewSet):
    """Friendship management"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserFriendshipSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Friends found.")
        return UserFriendship.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def send_request(self, request):
        """Send friend request"""
        friend_username = request.data.get('username')
        if not friend_username:
            return Response({'error': 'Username required'}, status=400)
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            friend = User.objects.get(username=friend_username)
            
            if friend == request.user:
                return Response({'error': 'Cannot add yourself as friend'}, status=400)
            
            # Check if friendship already exists
            existing = UserFriendship.objects.filter(
                Q(user=request.user, friend=friend) |
                Q(user=friend, friend=request.user)
            ).first()
            
            if existing:
                return Response({'error': 'Friend request already exists'}, status=400)
            
            # Create friendship
            friendship = UserFriendship.objects.create(
                user=request.user,
                friend=friend,
                status='pending'
            )
            
            # Create notification for friend
            Notification.objects.create(
                user=friend,
                notification_type='friend_request',
                title='New Friend Request',
                message=f'{request.user.username} wants to be your friend!',
                data={'friendship_id': friendship.id}
            )
            
            return Response({'message': 'Friend request sent'})
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    
    @action(detail=True, methods=['post'])
    def accept_request(self, request, pk=None):
        """Accept friend request"""
        friendship = get_object_or_404(UserFriendship, id=pk, friend=request.user, status='pending')
        friendship.status = 'accepted'
        friendship.save()
        
        # Create reverse friendship
        UserFriendship.objects.get_or_create(
            user=request.user,
            friend=friendship.user,
            defaults={'status': 'accepted'}
        )
        
        return Response({'message': 'Friend request accepted'})
    
    @action(detail=True, methods=['post'])
    def reject_request(self, request, pk=None):
        """Reject friend request"""
        friendship = get_object_or_404(UserFriendship, id=pk, friend=request.user, status='pending')
        friendship.delete()
        
        return Response({'message': 'Friend request rejected'})

# ============ MISSION VIEWS ============

class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Mission management"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserMissionSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Missions found Available.")
        return UserMission.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def available_missions(self, request):
        """Get available missions for user"""
        user = request.user
        user_level = getattr(user.progress_profile, 'current_level', 0)
        
        # Get active missions count
        active_count = UserMission.objects.filter(user=user, status='active').count()
        max_missions = 5  # Maximum concurrent missions
        
        if active_count >= max_missions:
            return Response({
                'available_missions': [],
                'message': f'You have reached the maximum of {max_missions} active missions'
            })
        
        # Get suitable mission templates
        templates = MissionTemplate.objects.filter(
            is_active=True,
            min_user_level__lte=user_level
        )
        
        if templates.exists():
            templates = templates.filter(
                Q(max_user_level__isnull=True) | Q(max_user_level__gte=user_level)
            )
        
        # Filter out recently completed missions (for non-repeatable missions)
        recent_completions = UserMission.objects.filter(
            user=user,
            status='completed',
            completed_at__gte=timezone.now() - timedelta(days=7)
        ).values_list('template_id', flat=True)
        
        available_templates = templates.exclude(
            id__in=recent_completions,
            is_repeatable=False
        )
        
        serializer = MissionTemplateSerializer(available_templates, many=True)
        return Response({
            'available_missions': serializer.data,
            'active_missions_count': active_count,
            'max_missions': max_missions
        })
    
    @action(detail=False, methods=['post'])
    def accept_mission(self, request):
        """Accept a mission"""
        template_id = request.data.get('template_id')
        try:
            template_id = int(template_id)
            if template_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'Invalid template_id. Must be a positive integer.'}, status=400)
        template = get_object_or_404(MissionTemplate, id=template_id, is_active=True)

        # if not template_id:
        #     return Response({'error': 'Template ID required'}, status=400)
        
        template = get_object_or_404(MissionTemplate, id=template_id, is_active=True)
        user = request.user
        
        # Check if user can accept this mission
        user_level = getattr(user.progress_profile, 'current_level', 0)
        if user_level < template.min_user_level:
            return Response({'error': 'Insufficient level'}, status=400)
        
        if template.max_user_level and user_level > template.max_user_level:
            return Response({'error': 'Level too high for this mission'}, status=400)
        
        # Check active missions limit
        active_count = UserMission.objects.filter(user=user, status='active').count()
        if active_count >= 5:
            return Response({'error': 'Maximum active missions reached'}, status=400)
        
        # Create user mission
        end_date = timezone.now() + timedelta(days=template.duration_days)
        mission = UserMission.objects.create(
            user=user,
            template=template,
            title=template.name,
            description=template.description,
            target_value=template.target_value,
            end_date=end_date,
            xp_reward=template.xp_reward,
            bonus_multiplier=template.bonus_multiplier,
            category=template.category
        )
        
        # Create notification
        Notification.objects.create(
            user=user,
            notification_type='mission_accepted',
            title='New Mission Accepted!',
            message=f'You accepted the mission "{template.name}". Complete it within {template.duration_days} days!',
            data={'mission_id': mission.id}
        )
        
        serializer = UserMissionSerializer(mission)
        return Response({
            'mission': serializer.data,
            'message': 'Mission accepted successfully'
        })
    
    @action(detail=False, methods=['post'])
    def generate_random_missions(self, request):
        """Generate random missions for user"""
        
        count_str = request.data.get('count', '3')
        try:
            count = min(int(count_str), 5)
            if count <= 0:
                raise ValueError
        except ValueError:
            return Response({'error': 'Invalid count parameter. Must be a positive integer.'}, status=400)
        
        user = request.user
        user_level = getattr(user.progress_profile, 'current_level', 0)
        count = min(int(request.data.get('count', 3)), 5)
        
        # Get suitable templates
        templates = MissionTemplate.objects.filter(
            is_active=True,
            min_user_level__lte=user_level
        )
        
        if templates.exists():
            templates = templates.filter(
                Q(max_user_level__isnull=True) | Q(max_user_level__gte=user_level)
            )
        
        # Select random templates based on weight
        selected_templates = []
        template_list = list(templates)
        
        for _ in range(min(count, len(template_list))):
            weights = [t.weight for t in template_list]
            selected = random.choices(template_list, weights=weights, k=1)[0]
            selected_templates.append(selected)
            template_list.remove(selected)
        
        serializer = MissionTemplateSerializer(selected_templates, many=True)
        return Response({
            'generated_missions': serializer.data,
            'count': len(selected_templates)
        })
    
    @action(detail=True, methods=['post'])
    def abandon_mission(self, request, pk=None):
        """Abandon an active mission"""
        mission = get_object_or_404(UserMission, id=pk, user=request.user, status='active')
        mission.status = 'abandoned'
        mission.save()
        
        return Response({'message': 'Mission abandoned'})
    
    @action(detail=False, methods=['get'])
    def mission_progress(self, request):
        """Get detailed progress for all active missions"""
        missions = UserMission.objects.filter(user=request.user, status='active')
        progress_data = []
        
        for mission in missions:
            progress_data.append({
                'mission': UserMissionSerializer(mission).data,
                'progress_percentage': mission.progress_percentage,
                'time_remaining': mission.time_remaining,
                'is_expired': mission.is_expired
            })
        
        return Response({'mission_progress': progress_data})
    
    @action(detail=False, methods=['post'])
    def update_mission_progress(self, request):
        """Check and update mission progress based on recent tasks"""
        from .gamification import MissionService
        
        user = request.user
        
        # Get mission_type from request or default
        mission_type = request.data.get('mission_type', 'default')  # you can decide a default
        
        updated_missions = MissionService.update_mission_progress(
            user_id=user.id,
            mission_type=mission_type,
            progress_value=1
        )
        
        return Response({
            'updated_missions': len(updated_missions),
            'missions': UserMissionSerializer(updated_missions, many=True).data
        })


# ============ NOTIFICATION VIEWS ============

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification management"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Notificationns found.")
        return Notification.objects.filter(
            user=self.request.user,
            is_archived=False
        ).select_related('user').order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_archived=False
        ).count()
        
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'marked_read': updated})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark specific notification as read"""
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.mark_as_read()
        
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive specific notification"""
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.archive()
        
        return Response({'message': 'Notification archived'})
    
    @action(detail=False, methods=['post'])
    def archive_all_read(self, request):
        """Archive all read notifications"""
        updated = Notification.objects.filter(
            user=request.user,
            is_read=True,
            is_archived=False
        ).update(is_archived=True)
        
        return Response({'archived': updated})
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications grouped by type"""
        notification_type = request.query_params.get('type')
        
        queryset = self.get_queryset()
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        notifications = queryset[:20]
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'notifications': serializer.data,
            'type': notification_type
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 24 hours)"""
        since = timezone.now() - timedelta(hours=24)
        notifications = self.get_queryset().filter(created_at__gte=since)
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'recent_notifications': serializer.data,
            'count': notifications.count()
        })

class NotificationSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification settings management"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSettingsSerializer
    
    def get_object(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("Notification settings not available.")
        settings, created = UserNotificationSettings.objects.get_or_create(
            user=self.request.user
        )
        return settings
    
    @action(detail=False, methods=['get'])
    def get_settings(self, request):
        """Get current notification settings"""
        settings = self.get_object()
        if settings is None:
            return Response(status=404)

        serializer = UserNotificationSettingsSerializer(settings)
        return Response(serializer.data)

    
    @action(detail=False, methods=['post'])
    def update_settings(self, request):
        """Update notification settings"""
        settings = self.get_object()
        if settings is None:
            return Response(status=404)        
        serializer = UserNotificationSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Settings updated successfully',
                'settings': serializer.data
            })
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['get'])
    def notification_types(self, request):
        """Get available notification types"""
        types = NotificationType.objects.all()
        serializer = NotificationTypeSerializer(types, many=True)
        return Response({'notification_types': serializer.data})

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            raise NotFound("No Profile found.")
        return UserNotificationSettings.objects.filter(user=self.request.user).order_by('-created_at')

# ============ UTILITY VIEWS ============

class GameStatsViewSet(viewsets.ViewSet):
    """General game statistics and utilities"""
    permission_classes = [IsAuthenticated]
  
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get summary data for gamification dashboard"""
        user = request.user

        try:
            # Get active missions
            active_missions = UserMission.objects.filter(user=user, status='active')

            # Get recent notifications (last 3 days)
            recent_notifications = Notification.objects.filter(
                user=user,
                is_read=False,
                created_at__gte=timezone.now() - timedelta(days=3)
            )[:5]

            # Get leaderboard position
            user_rank = self._get_user_global_rank(user)

            # Get weekly stats
            week_start = timezone.now() - timedelta(days=7)
            from .models import Task
            weekly_tasks = Task.objects.filter(
                user=user,
                completed_at__gte=week_start,
                is_completed=True
            ).count()

            # ✅ Normal response
            return Response({
                'active_missions': UserMissionSerializer(active_missions, many=True).data,
                'recent_notifications': NotificationSerializer(recent_notifications, many=True).data,
                'global_rank': user_rank,
                'weekly_tasks_completed': weekly_tasks,
                'unread_notifications': recent_notifications.count()
            })

        except Exception as e:
            # ✅ Log the error properly
            logger.exception(f"Error generating dashboard summary for user {user.id}: {str(e)}")

            # ✅ Return a structured error response
            return Response({
                "detail": "An unexpected error occurred while generating the dashboard summary."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_user_global_rank(self, user):
        """Get user's current global rank"""
        try:
            user_entry = LeaderboardEntry.objects.filter(user=user).first()
            if user_entry:
                return user_entry.rank
        except Exception:
            logging.exception("Failed to get user global rank")
        return None

    @action(detail=False, methods=['post'])
    def send_test_notification(self, request):
        """Send test notification (for development)"""
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=403)
        
        Notification.objects.create(
            user=request.user,
            notification_type='test',
            title='Test Notification',
            message='This is a test notification from the system.',
            data={'test': True}
        )
        
        return Response({'message': 'Test notification sent'})
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """Get system-wide statistics"""
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=403)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        stats = {
            'total_users': User.objects.count(),
            'active_missions': UserMission.objects.filter(status='active').count(),
            'completed_missions': UserMission.objects.filter(status='completed').count(),
            'total_notifications': Notification.objects.count(),
            'unread_notifications': Notification.objects.filter(is_read=False).count(),
            'active_friendships': UserFriendship.objects.filter(status='accepted').count(),
            'pending_friend_requests': UserFriendship.objects.filter(status='pending').count(),
        }
        
        return Response({'system_stats': stats})

def index(request):
    return render(request, 'index.html')
