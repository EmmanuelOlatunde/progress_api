import uuid
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile

from users.models import CustomUser, UserActivity, PasswordResetToken, UserProfile
from users.serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserStatsSerializer
)

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common setup and utility methods"""
    
    @classmethod
    def setUpTestData(self):
        """Set up test data that doesn't change between tests"""
        self.default_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        self.complete_user_data = {
            'username': 'completeuser',
            'email': 'complete@example.com',
            'password': 'testpass123',
            'first_name': 'Complete',
            'last_name': 'User',
            'bio': 'Test bio',
            'location': 'Test City'
        }
        
        self.profile_data = {
            'job_title': 'Software Developer',
            'company': 'Tech Corp',
            'skills': 'Python, Django, JavaScript',
            'preferred_languages': 'Python, JavaScript, Go',
            'learning_goals': 'Learn more about AI'
        }
    
    def create_user(self, **kwargs):
        """Create a user with default data, allowing overrides"""
        user_data = self.default_user_data.copy()
        user_data.update(kwargs)
        return CustomUser.objects.create_user(**user_data)
    
    def create_superuser(self, **kwargs):
        """Create a superuser with default data, allowing overrides"""
        user_data = self.default_user_data.copy()
        user_data.update(kwargs)
        return CustomUser.objects.create_superuser(**user_data)
    
    def create_profile(self, user, **kwargs):
        """Create a user profile with default data, allowing overrides"""
        profile_data = self.profile_data.copy()
        profile_data.update(kwargs)
        profile_data['user'] = user
        return UserProfile.objects.create(**profile_data)
    
    def create_reset_token(self, user, **kwargs):
        """Create a password reset token"""
        token_data = {'user': user}
        token_data.update(kwargs)
        return PasswordResetToken.objects.create(**token_data)
    
    def create_activity(self, user, activity_type='login', **kwargs):
        """Create a user activity"""
        activity_data = {
            'user': user,
            'activity_type': activity_type,
            'ip_address': '127.0.0.1'
        }
        activity_data.update(kwargs)
        return UserActivity.objects.create(**activity_data)
    
    def create_test_avatar(self, filename="test_avatar.jpg"):
        """Create a test avatar file"""
        return SimpleUploadedFile(
            filename,
            b"file_content",
            content_type="image/jpeg"
        )
    
    def assert_user_attributes(self, user, expected_data):
        """Assert user attributes match expected data"""
        for attr, expected_value in expected_data.items():
            if attr != 'password':
                self.assertEqual(getattr(user, attr), expected_value)
    
    def assert_profile_skills(self, profile, expected_skills):
        """Assert profile skills match expected list"""
        self.assertEqual(profile.get_skills_list(), expected_skills)
    
    def assert_profile_languages(self, profile, expected_languages):
        """Assert profile languages match expected list"""
        self.assertEqual(profile.get_preferred_languages_list(), expected_languages)


class CustomUserModelTests(BaseTestCase):
    """Test cases for CustomUser model"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = self.create_user()
        
        self.assert_user_attributes(user, {
            'email': 'test@example.com',
            'username': 'testuser',
            'is_staff': False,
            'is_superuser': False
        })
        self.assertTrue(user.check_password('testpass123'))
        self.assertIsInstance(user.id, uuid.UUID)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = self.create_superuser()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = self.create_user()
        self.assertEqual(str(user), 'test@example.com')
    
    def test_full_name_property(self):
        """Test full_name property"""
        user = self.create_user()
        self.assertEqual(user.full_name, 'Test User')
        
        # Test with no first/last name
        user.first_name = ''
        user.last_name = ''
        self.assertEqual(user.full_name, 'testuser')
    
    def test_display_name_property(self):
        """Test display_name property"""
        user = self.create_user()
        self.assertEqual(user.display_name, 'Test User')
    
    def test_get_avatar_url(self):
        """Test get_avatar_url method"""
        user = self.create_user()
        self.assertEqual(user.get_avatar_url(), '/static/images/default-avatar.png')
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        self.create_user()
        with self.assertRaises(IntegrityError):
            self.create_user(username='testuser2')
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        user = self.create_user()
        
        # Valid phone number
        user.phone_number = '+1234567890'
        user.full_clean()  # Should not raise
        
        # Invalid phone number
        user.phone_number = 'invalid-phone'
        with self.assertRaises(ValidationError):
            user.full_clean()


class UserProfileModelTests(BaseTestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user()
        self.profile = self.user.profile
    
    def test_profile_creation(self):
        """Test profile creation"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.total_points, 0)
        self.assertEqual(self.profile.current_streak, 0)
    
    def test_profile_string_representation(self):
        """Test profile string representation"""
        expected = f"{self.user.username}'s Profile"
        self.assertEqual(str(self.profile), expected)
    
    def test_increment_profile_views(self):
        """Test profile view increment"""
        initial_views = self.profile.profile_views
        self.profile.increment_profile_views()
        self.assertEqual(self.profile.profile_views, initial_views + 1)
    
    def test_profile_completeness_calculation(self):
        """Test profile completeness calculation with different data levels"""

        # Test empty profile — user created with minimal info, profile auto-created empty
        # empty_user = self.create_user(username='empty', email='empty@example.com')
        # empty_profile = empty_user.profile
        # self.assertEqual(empty_profile.calculate_completeness(), 0)

        # Test partial profile — update user/profile fields after creation
        partial_user = self.create_user(
            username='partial',
            email='partial@example.com',
            first_name='Partial',
            last_name='User',
            bio='Test bio'
        )
        # Since profile is created automatically, update it like this:
        partial_user.profile.job_title = 'Developer'
        partial_user.profile.skills = 'Python, Django'
        partial_user.profile.save()

        partial_completeness = partial_user.profile.calculate_completeness()
        self.assertEqual(partial_completeness, 50)  # For example, 5 out of 10 fields

        # Test complete profile — fill all fields on user and profile
        complete_user = self.create_user(
            username='complete',
            email='complete@example.com',
            first_name='Complete',
            last_name='User',
            bio='Test bio',
            location='Test City'
        )
        complete_user.avatar = self.create_test_avatar()
        complete_user.save()

        # Update profile fields if needed to mark as complete
        profile = complete_user.profile
        # Set all required fields on the profile here
        profile.job_title = 'Senior Developer'
        profile.skills = 'Python, Django, REST, Docker'
        profile.company= 'Freelance'
        profile.preferred_languages= 'English'
        profile.learning_goals= 'Tech bro'

        profile.save()

        self.assertEqual(profile.calculate_completeness(), 100)

    def test_skills_and_languages_parsing(self):
        """Test parsing of skills and languages lists"""
        test_cases = [
            ('Python, Django, JavaScript', ['Python', 'Django', 'JavaScript']),
            ('Python,  Django  , JavaScript ,  ', ['Python', 'Django', 'JavaScript']),
            ('Python', ['Python']),
            ('', [])
        ]
        
        for input_str, expected_list in test_cases:
            with self.subTest(input_str=input_str):
                self.profile.skills = input_str
                self.profile.preferred_languages = input_str
                self.assert_profile_skills(self.profile, expected_list)
                self.assert_profile_languages(self.profile, expected_list)


class PasswordResetTokenModelTests(BaseTestCase):
    """Test cases for PasswordResetToken model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user()
    
    def test_token_creation_and_properties(self):
        """Test token creation and basic properties"""
        token = self.create_reset_token(self.user)
        
        self.assertEqual(token.user, self.user)
        self.assertIsNotNone(token.token)
        self.assertIsNotNone(token.expires_at)
        self.assertFalse(token.is_used)
        self.assertIsInstance(token.token, uuid.UUID)
    
    def test_token_expiration_and_validity(self):
        """Test token expiration and validity logic"""
        # Valid token
        valid_token = self.create_reset_token(self.user)
        self.assertTrue(valid_token.is_valid())
        self.assertFalse(valid_token.is_expired())
        
        # Expired token
        expired_token = self.create_reset_token(
            self.user, 
            expires_at=timezone.now() - timedelta(hours=2)
        )
        self.assertTrue(expired_token.is_expired())
        self.assertFalse(expired_token.is_valid())
        
        # Used token
        used_token = self.create_reset_token(self.user, is_used=True)
        self.assertFalse(used_token.is_valid())
    
    def test_token_workflow(self):
        """Test complete password reset token workflow"""
        token = self.create_reset_token(self.user)
        
        # Initial state
        self.assertTrue(token.is_valid())
        self.assertFalse(token.is_expired())
        self.assertFalse(token.is_used)
        
        # After use
        token.is_used = True
        token.save()
        self.assertFalse(token.is_valid())
    
    def test_token_string_representation(self):
        """Test token string representation"""
        token = self.create_reset_token(self.user)
        expected = f"Password reset token for {self.user.email}"
        self.assertEqual(str(token), expected)
    
    def test_token_uniqueness(self):
        """Test that each token has a unique UUID"""
        token1 = self.create_reset_token(self.user)
        token2 = self.create_reset_token(self.user)
        self.assertNotEqual(token1.token, token2.token)
    
    def test_automatic_expires_at_setting(self):
        """Test automatic expires_at setting"""
        token = PasswordResetToken(user=self.user)
        self.assertIsNone(token.expires_at)
        
        token.save()
        self.assertIsNotNone(token.expires_at)
        
        # Should be approximately 1 hour from now
        expected_expiry = timezone.now() + timedelta(hours=1)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance


class UserActivityModelTests(BaseTestCase):
    """Test cases for UserActivity model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user()
    
    def test_activity_creation(self):
        """Test activity creation"""
        activity = self.create_activity(self.user, 'login')
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.ip_address, '127.0.0.1')
    
    def test_activity_string_representation(self):
        """Test activity string representation"""
        activity = self.create_activity(self.user, 'login')
        expected = f"{self.user.username} - login at {activity.timestamp}"
        self.assertEqual(str(activity), expected)
    
    def test_activity_tracking_and_ordering(self):
        """Test user activity tracking and ordering"""
        # Create activities with different timestamps
        activity1 = self.create_activity(self.user, 'login')
        activity1.timestamp = timezone.now() - timedelta(seconds=1)
        activity1.save()
        
        activity2 = self.create_activity(self.user, 'task_create')
        activity2.timestamp = timezone.now()
        activity2.save()
        
        # Test retrieval and ordering
        user_activities = UserActivity.objects.filter(
            user=self.user
        ).order_by('-timestamp')
        
        self.assertEqual(user_activities.count(), 2)
        self.assertEqual(user_activities[0].activity_type, 'task_create')
        self.assertEqual(user_activities[1].activity_type, 'login')


class SerializerTestsMixin:
    """Mixin providing common serializer test methods"""
    
    def assert_serializer_valid(self, serializer_class, data, expected_user_data=None):
        """Assert serializer is valid and optionally check user data"""
        serializer = serializer_class(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        if expected_user_data:
            user = serializer.save()
            self.assert_user_attributes(user, expected_user_data)
            return user
        
        return serializer
    
    def assert_serializer_invalid(self, serializer_class, data, expected_error_fields=None):
        """Assert serializer is invalid and optionally check error fields"""
        serializer = serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        
        if expected_error_fields:
            for field in expected_error_fields:
                self.assertIn(field, serializer.errors)
        
        return serializer


class UserRegistrationSerializerTests(BaseTestCase, SerializerTestsMixin):
    """Test cases for UserRegistrationSerializer"""
    
    def test_valid_registration(self):
        """Test valid user registration"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user = self.assert_serializer_valid(
            UserRegistrationSerializer, 
            data, 
            {'email': 'test@example.com'}
        )
        self.assertTrue(user.check_password('complexpassword123'))
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'differentpassword',
        }
        
        self.assert_serializer_invalid(
            UserRegistrationSerializer, 
            data, 
            ['non_field_errors']
        )
    
    def test_duplicate_email(self):
        """Test duplicate email validation"""
        self.create_user(username='existing')
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
        }
        
        self.assert_serializer_invalid(
            UserRegistrationSerializer, 
            data, 
            ['email']
        )


class UserLoginSerializerTests(BaseTestCase, SerializerTestsMixin):
    """Test cases for UserLoginSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user()
    
    def test_valid_login(self):
        """Test valid login"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        serializer = self.assert_serializer_valid(UserLoginSerializer, data)
        self.assertEqual(serializer.validated_data['user'], self.user)
    
    def test_invalid_credentials(self):
        """Test invalid login credentials"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        self.assert_serializer_invalid(UserLoginSerializer, data)
    
    def test_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        self.assert_serializer_invalid(UserLoginSerializer, data)

    
class UserStatsSerializerTests(BaseTestCase):
    """Test cases for UserStatsSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user1 = self.create_user(username='user1', email='user1@example.com')
        self.user2 = self.create_user(
            username='user2', 
            email='user2@example.com',
            is_profile_public=True
        )
        
        # Set recent login for active user test
        self.user1.last_login = timezone.now()
        self.user1.save()
    
    def test_stats_calculation(self):
        """Test user statistics calculation"""
        serializer = UserStatsSerializer()
        data = serializer.to_representation(None)
        
        required_fields = ['total_users', 'active_users', 'public_profiles', 'recent_registrations']
        for field in required_fields:
            self.assertIn(field, data)
        
        self.assertGreaterEqual(data['total_users'], 2)
        self.assertGreaterEqual(data['public_profiles'], 1)


class IntegrationTests(BaseTestCase):
    """Integration tests for model interactions"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user()
    
    def test_user_profile_relationship(self):
        """Test user-profile relationship"""
        try:
            profile = self.user.profile
            self.assertIsInstance(profile, UserProfile)
        except UserProfile.DoesNotExist:
            # Create profile manually if no signal exists
            profile = UserProfile.objects.create(user=self.user)
            self.assertIsInstance(profile, UserProfile)
    
    def test_password_reset_token_relationships(self):
        """Test password reset token relationships"""
        token1 = self.create_reset_token(self.user)
        token2 = self.create_reset_token(self.user)
        
        # Test forward relationship
        self.assertEqual(token1.user, self.user)
        
        # Test reverse relationship
        user_tokens = self.user.passwordresettoken_set.all()
        self.assertEqual(user_tokens.count(), 2)
        self.assertIn(token1, user_tokens)
        self.assertIn(token2, user_tokens)
    
    def test_user_activity_relationship(self):
        """Test user activity relationship"""
        activity1 = self.create_activity(self.user, 'login')
        activity2 = self.create_activity(self.user, 'logout')
        
        user_activities = self.user.activities.all()
        self.assertEqual(user_activities.count(), 2)
        self.assertIn(activity1, user_activities)
        self.assertIn(activity2, user_activities)