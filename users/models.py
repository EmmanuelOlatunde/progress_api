# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    Adds additional fields for profile management and public visibility
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    
    # Profile fields
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    
    # Phone number with validation
    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. 9 to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    # Account settings
    is_profile_public = models.BooleanField(
        default=False,
        help_text="Make your profile publicly viewable"
    )
    email_notifications = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users_customuser'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Return the user's full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def display_name(self):
        """Return display name for public profiles"""
        return self.full_name if self.full_name else self.username
    
    def get_avatar_url(self):
        """Return avatar URL or default"""
        if self.avatar:
            return self.avatar.url
        return '/static/images/default-avatar.png'


class UserProfile(models.Model):
    """
    Extended profile information for users
    Separates core user data from extended profile data
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Social links
    github_username = models.CharField(max_length=39, blank=True)  # GitHub max username length
    linkedin_url = models.URLField(blank=True)
    twitter_username = models.CharField(max_length=15, blank=True)  # Twitter max username length
    
    # Professional info
    job_title = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills")
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        blank=True
    )
    
    # Learning preferences
    preferred_languages = models.TextField(
        blank=True,
        help_text="Comma-separated list of programming languages"
    )
    learning_goals = models.TextField(blank=True)
    
    # Progress tracking fields (for future features)
    total_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(blank=True, null=True)
    
    # Profile statistics
    profile_views = models.PositiveIntegerField(default=0)
    profile_completeness = models.PositiveIntegerField(default=0)  # Percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users_userprofile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def increment_profile_views(self):
        """Increment profile view count"""
        self.profile_views += 1
        self.save(update_fields=['profile_views'])
    
    def calculate_completeness(self):
        """Calculate profile completeness percentage"""
        fields_to_check = [
            self.user.first_name,
            self.user.last_name,
            self.user.bio,
            self.user.avatar,
            self.user.location,
            self.job_title,
            self.company,
            self.skills,
            self.preferred_languages,
            self.learning_goals,
        ]
        
        filled_fields = sum(1 for field in fields_to_check if field and field != '')
        completeness = int((filled_fields / len(fields_to_check)) * 100)
        
        if self.profile_completeness != completeness:
            self.profile_completeness = completeness
            self.save(update_fields=['profile_completeness'])
        
        return completeness
    
    def get_skills_list(self):
        """Return skills as a list"""
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]
    
    def get_preferred_languages_list(self):
        """Return preferred languages as a list"""
        return [lang.strip() for lang in self.preferred_languages.split(',') if lang.strip()]


class UserActivity(models.Model):
    """
    Track user activity for engagement metrics
    Useful for profile statistics and streak calculations
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('login', 'Login'),
            ('profile_update', 'Profile Update'),
            ('profile_view', 'Profile Viewed'),
            ('password_change', 'Password Change'),
            ('email_change', 'Email Change'),
        ]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'users_useractivity'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"


class PasswordResetToken(models.Model):
    """
    Custom password reset token model for additional security
    Can be used alongside or instead of default Django tokens
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        db_table = 'users_passwordresettoken'
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Token expires in 1 hour
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    def __str__(self):
        return f"Password reset token for {self.user.email}"


