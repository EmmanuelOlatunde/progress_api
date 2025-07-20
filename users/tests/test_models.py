import uuid
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
import time

from users.models import CustomUser, UserProfile, UserActivity, PasswordResetToken

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common setup and utility methods"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        cls.default_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        cls.complete_user_data = {
            'username': 'completeuser',
            'email': 'complete@example.com',
            'password': 'testpass123',
            'first_name': 'Complete',
            'last_name': 'User',
            'bio': 'Test bio',
            'location': 'Test City',
            'website': 'https://example.com',
            'phone_number': '+1234567890'
        }
        
        cls.profile_data = {
            'job_title': 'Software Developer',
            'company': 'Tech Corp',
            'skills': 'Python, Django, JavaScript',
            'preferred_languages': 'Python, JavaScript, Go',
            'learning_goals': 'Learn more about AI',
            'github_username': 'testgithub',
            'linkedin_url': 'https://linkedin.com/in/testuser',
            'twitter_username': 'testuser',
            'experience_level': 'intermediate'
        }
    
    def create_user(self, **kwargs):
        """Create a user with default data, allowing overrides, ensuring unique email and username"""
        user_data = self.default_user_data.copy()
        user_data.update(kwargs)
        # Ensure unique email and username by appending UUID if not overridden
        if 'email' not in kwargs:
            user_data['email'] = f"{user_data['email'].split('@')[0]}-{uuid.uuid4()}@example.com"
        if 'username' not in kwargs:
            user_data['username'] = f"{user_data['username']}-{uuid.uuid4().hex[:8]}"
        return CustomUser.objects.create_user(**user_data)
    
    def create_superuser(self, **kwargs):
        """Create a superuser with default data, allowing overrides"""
        user_data = self.default_user_data.copy()
        user_data.update(kwargs)
        # Ensure unique email and username for superuser
        if 'email' not in kwargs:
            user_data['email'] = f"{user_data['email'].split('@')[0]}-{uuid.uuid4()}@example.com"
        if 'username' not in kwargs:
            user_data['username'] = f"{user_data['username']}-{uuid.uuid4().hex[:8]}"
        return CustomUser.objects.create_superuser(**user_data)
    
    def create_profile(self, user, **kwargs):
        """Update the automatically created user profile with default data, allowing overrides"""
        profile = user.profile  # Assumes profile is auto-created via signal
        profile_data = self.profile_data.copy()
        profile_data.update(kwargs)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        return profile
    
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
            'email': user.email,  # Dynamic email from create_user
            'username': user.username,  # Dynamic username
            'first_name': 'Test',
            'last_name': 'User',
            'is_staff': False,
            'is_superuser': False,
            'is_profile_public': False,
            'email_notifications': True
        })
        self.assertTrue(user.check_password('testpass123'))
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = self.create_superuser()
        self.assert_user_attributes(user, {
            'email': user.email,  # Dynamic email
            'username': user.username,  # Dynamic username
            'is_staff': True,
            'is_superuser': True
        })
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = self.create_user()
        self.assertEqual(str(user), user.email)
    
    def test_full_name_property(self):
        """Test full_name property"""
        user = self.create_user()
        self.assertEqual(user.full_name, 'Test User')
        
        # Test with no first/last name
        user = self.create_user(username='testuser2', first_name='', last_name='', email='unique@example.com')
        self.assertEqual(user.full_name, 'testuser2')
    
    def test_display_name_property(self):
        """Test display_name property"""
        user = self.create_user()
        self.assertEqual(user.display_name, 'Test User')
        
        # Test with no first/last name
        user = self.create_user(username='testuser3', first_name='', last_name='', email='unique2@example.com')
        self.assertEqual(user.display_name, 'testuser3')
    
    def test_get_avatar_url(self):
        """Test get_avatar_url method"""
        user = self.create_user()
        self.assertEqual(user.get_avatar_url(), '/static/images/default-avatar.png')
        
        user.avatar = self.create_test_avatar()
        user.save()
        self.assertTrue(user.avatar.url.endswith('.jpg'))
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        self.create_user(email='unique1@example.com')
        with self.assertRaises(IntegrityError):
            self.create_user(email='unique1@example.com', username='testuser2')
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        user = self.create_user()
        
        # Valid phone numbers
        valid_numbers = ['+1234567890', '+12025550123']
        for number in valid_numbers:
            with self.subTest(number=number):
                user.phone_number = number
                user.full_clean()  # Should not raise
                user.save()  # Ensure save works
        
        # Invalid phone numbers
        invalid_numbers = ['invalid-phone', '12345', '+1234567890123456']
        for number in invalid_numbers:
            with self.subTest(number=number):
                user.phone_number = number
                with self.assertRaises(ValidationError):
                    user.full_clean()
                    user.save()  # This line won't execute if full_clean raises
    
    def test_complete_user(self):
        """Test creating a user with all fields"""
        user = self.create_user(**self.complete_user_data)
        self.assert_user_attributes(user, {
            'email': 'complete@example.com',
            'username': 'completeuser',
            'first_name': 'Complete',
            'last_name': 'User',
            'bio': 'Test bio',
            'location': 'Test City',
            'website': 'https://example.com',
            'phone_number': '+1234567890'
        })
    
    def test_last_login_ip(self):
        """Test last_login_ip field"""
        user = self.create_user(last_login_ip='192.168.1.1')
        self.assertEqual(user.last_login_ip, '192.168.1.1')
        
        user.last_login_ip = 'invalid-ip'
        with self.assertRaises(ValidationError):
            user.full_clean()


class UserProfileModelTests(BaseTestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user(email='setup@example.com')
        self.profile = self.user.profile  # Assumes profile is auto-created
    
    def test_profile_auto_creation(self):
        """Test that profile is automatically created with user"""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.total_points, 0)
        self.assertEqual(self.profile.current_streak, 0)
        self.assertEqual(self.profile.longest_streak, 0)
        self.assertEqual(self.profile.profile_views, 0)
        self.assertEqual(self.profile.profile_completeness, 0)
        self.assertIsNotNone(self.profile.created_at)
        self.assertIsNotNone(self.profile.updated_at)
    
    def test_profile_string_representation(self):
        """Test profile string representation"""
        self.assertEqual(str(self.profile), f"{self.user.username}'s Profile")
    
    def test_increment_profile_views(self):
        """Test profile view increment"""
        initial_views = self.profile.profile_views
        self.profile.increment_profile_views()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_views, initial_views + 1)
    
    def test_profile_completeness_calculation(self):
        """Test profile completeness calculation with different data levels"""
        # Test empty profile (only user fields from create_user)
        self.assertEqual(self.profile.calculate_completeness(), 20)  # first_name, last_name filled
        
        # Test partial profile
        partial_user = self.create_user(
            username='partial',
            email='partial@example.com',
            first_name='Partial',
            last_name='User',
            bio='Test bio'
        )
        partial_profile = self.create_profile(
            partial_user,
            job_title='Developer',
            skills='Python, Django',
            company='',  # Explicitly empty
            preferred_languages='',  # Explicitly empty
            learning_goals=''  # Explicitly empty
        )
        completeness = partial_profile.calculate_completeness()
        self.assertEqual(completeness, 50)  # 5/10 fields filled
        
        # Test complete profile
        complete_user = self.create_user(**self.complete_user_data)
        complete_user.avatar = self.create_test_avatar()
        complete_user.save()
        complete_profile = self.create_profile(complete_user)
        self.assertEqual(complete_profile.calculate_completeness(), 100)
    
    def test_skills_and_languages_parsing(self):
        """Test parsing of skills and languages lists"""
        test_cases = [
            ('Python, Django, JavaScript', ['Python', 'Django', 'JavaScript']),
            ('Python,  Django  , JavaScript ,  ', ['Python', 'Django', 'JavaScript']),
            ('Python', ['Python']),
            ('', []),
            (',,', [])
        ]
        
        for input_str, expected_list in test_cases:
            with self.subTest(input_str=input_str):
                self.profile.skills = input_str
                self.profile.preferred_languages = input_str
                self.profile.save()
                self.assert_profile_skills(self.profile, expected_list)
                self.assert_profile_languages(self.profile, expected_list)
    
    def test_social_links_validation(self):
        """Test social link field length constraints"""
        # Test GitHub username length
        self.profile.github_username = 'a' * 40  # Exceeds 39 chars
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        self.profile.github_username = 'validusername'
        self.profile.full_clean()  # Should not raise
        
        # Test Twitter username length
        self.profile.twitter_username = 'a' * 16  # Exceeds 15 chars
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        self.profile.twitter_username = 'testuser'
        self.profile.full_clean()  # Should not raise
    
    def test_experience_level_choices(self):
        """Test experience level choices"""
        valid_choices = ['beginner', 'intermediate', 'advanced', 'expert']
        for choice in valid_choices:
            with self.subTest(choice=choice):
                self.profile.experience_level = choice
                self.profile.full_clean()  # Should not raise
        
        self.profile.experience_level = 'invalid'
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
    
    def test_progress_fields(self):
        """Test progress-related fields in UserProfile"""
        self.profile.total_points = 100
        self.profile.current_streak = 5
        self.profile.longest_streak = 10
        self.profile.last_activity_date = timezone.now().date()
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_points, 100)
        self.assertEqual(self.profile.current_streak, 5)
        self.assertEqual(self.profile.longest_streak, 10)
        self.assertEqual(self.profile.last_activity_date, timezone.now().date())
    
    def test_unique_user_constraint(self):
        """Test that only one profile can exist per user"""
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)  # Profile already exists


class UserActivityModelTests(BaseTestCase):
    """Test cases for UserActivity model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user(email='activity@example.com')
    
    def test_activity_creation(self):
        """Test activity creation"""
        activity = self.create_activity(self.user, 'login')
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.ip_address, '127.0.0.1')
        self.assertIsNotNone(activity.timestamp)
        self.assertTrue(activity.user_agent == '')
    
    def test_activity_string_representation(self):
        """Test activity string representation"""
        activity = self.create_activity(self.user, 'login')
        expected = f"{self.user.username} - login at {activity.timestamp}"
        self.assertEqual(str(activity), expected)
    
    def test_activity_types(self):
        """Test all valid activity types"""
        activity_types = ['login', 'profile_update', 'profile_view', 'password_change', 'email_change']
        for activity_type in activity_types:
            with self.subTest(activity_type=activity_type):
                activity = self.create_activity(self.user, activity_type)
                activity.full_clean()  # Ensure choices are validated
                self.assertEqual(activity.activity_type, activity_type)
        
        invalid_activity = UserActivity(user=self.user, activity_type='invalid_type', ip_address='127.0.0.1')
        with self.assertRaises(ValidationError):
            invalid_activity.full_clean()
    
    def test_activity_ordering_and_indexes(self):
        """Test activity ordering and indexing"""
        self.create_activity(self.user, 'login', timestamp=timezone.now() - timedelta(seconds=3))
        time.sleep(0.01)  # Ensure distinct timestamps
        self.create_activity(self.user, 'profile_update', timestamp=timezone.now() - timedelta(seconds=2))
        time.sleep(0.01)
        self.create_activity(self.user, 'password_change', timestamp=timezone.now() - timedelta(seconds=1))
        
        # Test ordering by timestamp
        activities = UserActivity.objects.filter(user=self.user).order_by('-timestamp')
        self.assertEqual(activities.count(), 3)
        self.assertEqual(activities[0].activity_type, 'password_change')
        self.assertEqual(activities[1].activity_type, 'profile_update')
        self.assertEqual(activities[2].activity_type, 'login')
        
        # Test index usage (implicitly tested via query)
        indexed_query = UserActivity.objects.filter(user=self.user, activity_type='login').order_by('-timestamp')
        self.assertEqual(indexed_query.count(), 1)
    
    def test_user_agent_storage(self):
        """Test user agent storage"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        activity = self.create_activity(self.user, 'login', user_agent=user_agent)
        self.assertEqual(activity.user_agent, user_agent)
    
    def test_ip_address_validation(self):
        """Test IP address validation"""
        activity = self.create_activity(self.user, 'login', ip_address='192.168.1.1')
        self.assertEqual(activity.ip_address, '192.168.1.1')
        
        activity.ip_address = 'invalid-ip'
        with self.assertRaises(ValidationError):
            activity.full_clean()


class PasswordResetTokenModelTests(BaseTestCase):
    """Test cases for PasswordResetToken model"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = self.create_user(email='token@example.com')
    
    def test_token_creation_and_properties(self):
        """Test token creation and basic properties"""
        token = self.create_reset_token(self.user)
        self.assertEqual(token.user, self.user)
        self.assertIsInstance(token.token, uuid.UUID)
        self.assertIsNotNone(token.created_at)
        self.assertIsNotNone(token.expires_at)
        self.assertFalse(token.is_used)
        self.assertIsNone(token.ip_address)
    
    def test_token_expiration_and_validity(self):
        """Test token expiration and validity logic"""
        # Valid token
        token = self.create_reset_token(self.user)
        self.assertTrue(token.is_valid())
        self.assertFalse(token.is_expired())
        
        # Expired token
        expired_token = self.create_reset_token(self.user, expires_at=timezone.now() - timedelta(hours=2))
        self.assertTrue(expired_token.is_expired())
        self.assertFalse(expired_token.is_valid())
        
        # Used token
        used_token = self.create_reset_token(self.user, is_used=True)
        self.assertFalse(used_token.is_valid())
    
    def test_token_workflow(self):
        """Test complete password reset token workflow"""
        token = self.create_reset_token(self.user)
        self.assertTrue(token.is_valid())
        
        # Mark as used
        token.is_used = True
        token.save()
        self.assertFalse(token.is_valid())
        
        # Create new token
        new_token = self.create_reset_token(self.user)
        self.assertTrue(new_token.is_valid())
        self.assertNotEqual(new_token.token, token.token)
    
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
        
        expected_expiry = timezone.now() + timedelta(hours=1)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute tolerance
    
    def test_ip_address_storage(self):
        """Test IP address storage in token"""
        token = self.create_reset_token(self.user, ip_address='192.168.1.1')
        self.assertEqual(token.ip_address, '192.168.1.1')
        
        token.ip_address = 'invalid-ip'
        with self.assertRaises(ValidationError):
            token.full_clean()