
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
#from django.core.exceptions import ValidationError
from .models import CustomUser, UserProfile, UserActivity

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        """Validate username uniqueness"""
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def create(self, validated_data):
        """Create new user"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data"""
    skills_list = serializers.SerializerMethodField()
    preferred_languages_list = serializers.SerializerMethodField()
    profile_completeness = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = (
            'github_username', 'linkedin_url', 'twitter_username',
            'job_title', 'company', 'skills', 'skills_list',
            'experience_level', 'preferred_languages', 'preferred_languages_list',
            'learning_goals', 'total_points', 'current_streak', 'longest_streak',
            'profile_views', 'profile_completeness', 'created_at', 'updated_at'
        )
        read_only_fields = ('total_points', 'current_streak', 'longest_streak', 
                           'profile_views', 'created_at', 'updated_at')
    
    def get_skills_list(self, obj):
        return obj.get_skills_list()
    
    def get_preferred_languages_list(self, obj):
        return obj.get_preferred_languages_list()
    
    def get_profile_completeness(self, obj):
        return obj.calculate_completeness()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data"""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'bio', 'avatar', 'avatar_url', 'location', 'website', 'phone_number',
            'is_profile_public', 'email_notifications', 'date_joined',
            'last_login', 'profile'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

class PublicUserSerializer(serializers.ModelSerializer):
    """Serializer for public user profiles (limited fields)"""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'full_name', 'bio', 'avatar_url',
            'location', 'website', 'profile'
        )
    
    def get_full_name(self, obj):
        return obj.display_name
    
    def get_avatar_url(self, obj):
        return obj.get_avatar_url()
    
    def to_representation(self, instance):
        """Only return data if profile is public"""
        if not instance.is_profile_public:
            return {
                'message': 'This profile is private',
                'username': instance.username
            }
        return super().to_representation(instance)

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'bio', 'avatar', 'location',
            'website', 'phone_number', 'is_profile_public',
            'email_notifications', 'profile'
        )
    
    def update(self, instance, validated_data):
        """Update user and profile data"""
        profile_data = validated_data.pop('profile', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile fields
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance

class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value
    
    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def save(self):
        """Update user password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
    
    class Meta:
        fields = ['old_password', 'new_password', 'new_password_confirm']

class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Check if user with this email exists"""
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user found with this email address.')
        return value
    
    class Meta:
        fields = ['email']

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    class Meta:
        fields = ['token', 'new_password', 'new_password_confirm']

class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activity tracking"""
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = UserActivity
        fields = ('id', 'user', 'activity_type', 'timestamp', 'ip_address')
        read_only_fields = ('id', 'user', 'timestamp')

class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics dashboard"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    public_profiles = serializers.IntegerField()
    recent_registrations = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Calculate statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        total_users = CustomUser.objects.count()
        # Active users in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_users = CustomUser.objects.filter(last_login__gte=thirty_days_ago).count()
        public_profiles = CustomUser.objects.filter(is_profile_public=True).count()
        # Recent registrations in last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_registrations = CustomUser.objects.filter(date_joined__gte=seven_days_ago).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'public_profiles': public_profiles,
            'recent_registrations': recent_registrations,
        }