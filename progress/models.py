
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta


User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    xp_multiplier = models.FloatField(default=1.0)  # XP bonus for this category
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Task(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='tasks')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

    def complete_task(self):
        """Mark task as completed and award XP with timing validation"""
        if self.is_completed:
            return False, "Task is already completed"
        
        # Import here to avoid circular imports
        from .gamification import GamificationEngine
        engine = GamificationEngine(self.user)
        
        # Check if task can be completed
        can_complete, message = engine.can_complete_task(self)
        if not can_complete:
            return False, message
        
        # Complete the task
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
        
        # Award XP
        xp_earned, xp_message = engine.award_task_xp(self)
        return True, f"{xp_message}"

    def get_timing_info(self):
        """Get timing information for the task"""
        if not self.due_date:
            return {
                'status': 'no_deadline',
                'message': 'No deadline set',
                'can_complete': True
            }
        
        now = timezone.now()
        
        if self.is_completed:
            if self.completed_at <= self.due_date:
                return {
                    'status': 'completed_on_time',
                    'message': 'Completed on time',
                    'can_complete': True
                }
            else:
                days_late = (self.completed_at - self.due_date).days
                return {
                    'status': 'completed_late',
                    'message': f'Completed {days_late} day(s) late',
                    'can_complete': True
                }
        
        # For uncompleted tasks
        if now > self.due_date:
            days_overdue = (now - self.due_date).days
            return {
                'status': 'overdue',
                'message': f'Overdue by {days_overdue} day(s)',
                'can_complete': True
            }
        
        # Check minimum completion time
        from .gamification import GamificationEngine
        engine = GamificationEngine(self.user)
        can_complete, message = engine.can_complete_task(self)
        
        time_until_due = self.due_date - now
        hours_until_due = time_until_due.total_seconds() / 3600
        
        return {
            'status': 'pending',
            'message': f'Due in {int(hours_until_due)} hours',
            'can_complete': can_complete,
            'completion_message': message
        }

class XPLog(models.Model):
    ACTION_CHOICES = [
        ('task_complete', 'Task Completion'),
        ('streak_bonus', 'Streak Bonus'),
        ('achievement', 'Achievement Unlock'),
        ('daily_login', 'Daily Login'),
        ('bonus', 'Manual Bonus'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    xp_earned = models.IntegerField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} earned {self.xp_earned} XP for {self.get_action_display()}"

class ProgressProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress_profile')
    total_xp = models.IntegerField(default=0)
    current_level = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # New timing-based stats
    total_early_completions = models.IntegerField(default=0)
    total_on_time_completions = models.IntegerField(default=0)
    total_late_completions = models.IntegerField(default=0)
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.current_level}"

    @property
    def xp_for_current_level(self):
        """Total XP needed to reach current level"""
        return self.calculate_xp_for_level(self.current_level)
  
    @property
    def xp_for_next_level(self):
        """Total XP needed to reach next level"""
        return self.calculate_xp_for_level(self.current_level + 1)

    @property
    def xp_progress_in_current_level(self):
        """XP gained within current level"""
        return self.total_xp - self.xp_for_current_level

    @property
    def progress_percentage(self):
        """Progress percentage within current level"""
        xp_needed_for_level_segment = self.xp_for_next_level - self.xp_for_current_level
        if xp_needed_for_level_segment <= 0:
            return 100.0
        return (self.xp_progress_in_current_level / xp_needed_for_level_segment) * 100.0

    @property
    def xp_needed_for_next_level(self):
        """Calculate XP needed to reach next level"""
        return self.xp_for_next_level - self.total_xp

    def calculate_xp_for_level(self, level):
        """Calculate total XP needed to reach a specific level"""
        if level <= 1:
            return 0
        # Quadratic XP curve: level * 100
        # Level 1: 0, Level 2: 200, Level 3: 600, Level 4: 1200, etc.
        return sum(i * 100 for i in range(2, level + 1))

    def update_level(self):
        """Update user level based on XP"""
        # Level calculation: Each level requires 100 * level XP
        # Level 1: 0 XP, Level 2: 100 XP, Level 3: 300 XP, Level 4: 600 XP, etc.
        old_level = self.current_level
        level = 1
        
        # Find the highest level where total XP meets the requirement
        while self.total_xp >= self.calculate_xp_for_level(level + 1):
            level += 1
        
        self.current_level = level
        
        if self.current_level > old_level:
            self.save()
            from .gamification import GamificationEngine
            engine = GamificationEngine(self.user)
            engine.check_level_achievements(old_level, self.current_level)


    def punctuality_rate(self):
        """Calculate overall punctuality rate"""
        total_timed_tasks = (self.total_early_completions + 
                           self.total_on_time_completions + 
                           self.total_late_completions)
        if total_timed_tasks == 0:
            return 100
        return int(((self.total_early_completions + self.total_on_time_completions) / total_timed_tasks) * 100)

class Achievement(models.Model):
    ACHIEVEMENT_TYPES = [
        ('task_count', 'Task Count'),
        ('streak', 'Streak'),
        ('level', 'Level'),
        ('category', 'Category Mastery'),
        ('xp', 'XP Milestone'),
        ('special', 'Special'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50, default='🏆')  # Emoji or icon class
    threshold = models.IntegerField(help_text="Required value to unlock")
    xp_reward = models.IntegerField(default=50)
    is_hidden = models.BooleanField(default=False)  # Hidden until unlocked
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_achievement_type_display()})"

class UserAchievement(models.Model):
    """Track unlocked achievements for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)  # Current progress toward achievement

    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} unlocked {self.achievement.name}"

class WeeklyReview(models.Model):

    """Model to store weekly performance reviews"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_reviews')
    week_start = models.DateField()
    week_end = models.DateField()
    total_tasks = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)
    early_completions = models.IntegerField(default=0)
    on_time_completions = models.IntegerField(default=0)
    late_completions = models.IntegerField(default=0)
    performance_score = models.IntegerField(default=0)  # Score out of 100
    suggestions = models.TextField(blank=True)
    category_breakdown = models.JSONField(default=dict)  # Store category performance data
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_start']
        unique_together = ['user', 'week_start']

    def __str__(self):
        return f"Weekly Review for {self.user.username} - Week of {self.week_start}"

    @property
    def completion_rate(self):
        """Calculate task completion rate for tasks with deadlines"""
        total_timed_tasks = self.early_completions + self.on_time_completions + self.late_completions
        if total_timed_tasks == 0:
            return 0
        return int(((self.early_completions + self.on_time_completions) / total_timed_tasks) * 100)

    @property
    def punctuality_score(self):
        """Calculate punctuality score (early and on-time vs late)"""
        total_timed_tasks = self.early_completions + self.on_time_completions + self.late_completions
        if total_timed_tasks == 0:
            return 100
        return int(((self.early_completions * 2 + self.on_time_completions) / (total_timed_tasks * 2)) * 100)

    @property
    def performance_grade(self):
        """Return letter grade based on performance score"""
        if self.performance_score >= 90:
            return 'A+'
        elif self.performance_score >= 85:
            return 'A'
        elif self.performance_score >= 80:
            return 'B+'
        elif self.performance_score >= 75:
            return 'B'
        elif self.performance_score >= 70:
            return 'C+'
        elif self.performance_score >= 65:
            return 'C'
        elif self.performance_score >= 60:
            return 'D'
        else:
            return 'F'
        
# ============ MISSIONS ============

class MissionTemplate(models.Model):
    """Templates for generating missions"""
    MISSION_TYPES = [
        ('task_count', 'Complete X Tasks'),
        ('category_focus', 'Complete X Tasks in Category'),
        ('streak', 'Maintain X Day Streak'),
        ('timing', 'Complete X Tasks Early/On Time'),
        ('difficulty', 'Complete X Hard/Expert Tasks'),
        ('xp_target', 'Earn X XP'),
        ('daily_goal', 'Complete Daily Goal'),
        ('weekly_challenge', 'Weekly Challenge'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('legendary', 'Legendary'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    mission_type = models.CharField(max_length=20, choices=MISSION_TYPES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)
    
    # Mission parameters
    target_value = models.IntegerField(help_text="Target number to achieve")
    duration_days = models.IntegerField(default=7, help_text="Days to complete mission")
    
    # Rewards
    xp_reward = models.IntegerField()
    bonus_multiplier = models.FloatField(default=1.0)
    
    # Conditions
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    min_user_level = models.IntegerField(default=0)
    max_user_level = models.IntegerField(null=True, blank=True)
    
    # Availability
    is_active = models.BooleanField(default=True)
    is_repeatable = models.BooleanField(default=True)
    weight = models.IntegerField(default=1, help_text="Selection probability weight")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['difficulty', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_difficulty_display()})"

class UserMission(models.Model):
    """Active missions for users"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='missions')
    template = models.ForeignKey(MissionTemplate, on_delete=models.CASCADE)
    
    # Mission details
    title = models.CharField(max_length=200)
    description = models.TextField()
    target_value = models.IntegerField()
    current_progress = models.IntegerField(default=0)
    
    # Timing
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status and rewards
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    xp_reward = models.IntegerField()
    bonus_multiplier = models.FloatField(default=1.0)
    
    # Tracking
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    related_tasks = models.ManyToManyField('Task', blank=True, related_name='missions')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-end_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.target_value <= 0:
            return 100
        return min(100, int((self.current_progress / self.target_value) * 100))
    
    @property
    def is_expired(self):
        """Check if mission has expired"""
        return timezone.now() > self.end_date and self.status == 'active'
    
    @property
    def time_remaining(self):
        """Get time remaining for mission"""
        if self.status != 'active':
            return None
        return max(timedelta(0), self.end_date - timezone.now())
    
    def update_progress(self, increment=1):
        """Update mission progress"""
        if self.status != 'active':
            return False
        
        self.current_progress += increment
        
        if self.current_progress >= self.target_value:
            self.complete_mission()
        else:
            self.save()
        
        return True
    
    def complete_mission(self):
        """Mark mission as completed and award rewards"""
        if self.status != 'active':
            return False
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Award XP
        from .gamification import GamificationEngine
        engine = GamificationEngine(self.user)
        engine.award_mission_xp(self)
        
        # Create notification
        Notification.objects.create(
            user=self.user,
            notification_type='mission_completed',
            title='Mission Completed!',
            message=f'You completed "{self.title}" and earned {self.xp_reward} XP!',
            data={'mission_id': self.id, 'xp_earned': self.xp_reward}
        )
        
        return True
    
    def fail_mission(self):
        """Mark mission as failed"""
        if self.status != 'active':
            return False
        
        self.status = 'failed'
        self.save()
        
        # Create notification
        Notification.objects.create(
            user=self.user,
            notification_type='mission_failed',
            title='Mission Failed',
            message=f'Mission "{self.title}" has expired.',
            data={'mission_id': self.id}
        )
        
        return True

# ============ LEADERBOARDS ============

class LeaderboardType(models.Model):
    """Define different types of leaderboards"""
    LEADERBOARD_TYPES = [
        ('global', 'Global'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('category', 'Category-based'),
        ('friends', 'Friends Only'),
        ('company', 'Company/Team'),
    ]
    
    name = models.CharField(max_length=50)
    leaderboard_type = models.CharField(max_length=20, choices=LEADERBOARD_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    reset_frequency = models.CharField(
        max_length=20,
        choices=[
            ('never', 'Never'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='never'
    )
    category = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_leaderboard_type_display()})"

class LeaderboardEntry(models.Model):
    """Individual leaderboard entries"""
    leaderboard_type = models.ForeignKey(LeaderboardType, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    score = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    
    # Time period for the entry
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Additional stats
    tasks_completed = models.IntegerField(default=0)
    total_xp = models.IntegerField(default=0)
    streak_count = models.IntegerField(default=0)
    punctuality_rate = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['leaderboard_type', 'user', 'period_start']
        ordering = ['-score', '-updated_at']
        indexes = [
            models.Index(fields=['leaderboard_type', '-score']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.leaderboard_type.name} (Rank #{self.rank})"

class UserFriendship(models.Model):
    """Friend relationships for friend-based leaderboards"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_of')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('blocked', 'Blocked'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'friend']
    
    def __str__(self):
        return f"{self.user.username} -> {self.friend.username} ({self.status})"

# ============ NOTIFICATIONS ============

class NotificationType(models.Model):
    """Define different types of notifications"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_enabled = models.BooleanField(default=True)
    can_disable = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default='🔔')
    color = models.CharField(max_length=7, default='#007bff')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name

class Notification(models.Model):
    """User notifications"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Status
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Metadata
    data = models.JSONField(default=dict, blank=True)
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery
    delivered_via_email = models.BooleanField(default=False)
    delivered_via_push = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    push_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def archive(self):
        """Archive notification"""
        self.is_archived = True
        self.save(update_fields=['is_archived'])
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

class UserNotificationSettings(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    
    # Email notifications
    email_notifications = models.BooleanField(default=True)
    email_task_reminders = models.BooleanField(default=True)
    email_mission_updates = models.BooleanField(default=True)
    email_achievement_unlocks = models.BooleanField(default=True)
    email_leaderboard_updates = models.BooleanField(default=False)
    email_weekly_summary = models.BooleanField(default=True)
    
    # Push notifications
    push_notifications = models.BooleanField(default=True)
    push_task_reminders = models.BooleanField(default=True)
    push_mission_updates = models.BooleanField(default=True)
    push_achievement_unlocks = models.BooleanField(default=True)
    push_leaderboard_updates = models.BooleanField(default=False)
    
    # Frequency settings
    reminder_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='daily'
    )
    
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Notification Settings"

class NotificationQueue(models.Model):
    """Queue for scheduled notifications"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Delivery preferences
    send_email = models.BooleanField(default=False)
    send_push = models.BooleanField(default=True)
    
    # Tracking
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['user', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.username} - {self.title}"

# ============ HELPER MODELS ============

class SystemSetting(models.Model):
    """System-wide settings for gamification features"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    def get_value(self):
        """Return the value in the correct data type"""
        if self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        return self.value