from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from users.models import CustomUser, UserActivity
from users.serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserStatsSerializer,
    UserSerializer, PublicUserSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UserActivitySerializer
)

User = get_user_model()


class SerializerTestsMixin:
    """Mixin providing common serializer test methods"""
    
    def assert_serializer_valid(self, serializer_class, data, expected_user_data=None, context=None):
        """Assert serializer is valid and optionally check user data"""
        serializer = serializer_class(data=data, context=context)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        if expected_user_data:
            user = serializer.save()
            self.assert_user_attributes(user, expected_user_data)
            return user
        
        return serializer
    
    def assert_serializer_invalid(self, serializer_class, data, expected_error_fields=None, context=None):
        """Assert serializer is invalid and optionally check error fields"""
        serializer = serializer_class(data=data, context=context)
        self.assertFalse(serializer.is_valid())
        
        if expected_error_fields:
            for field in expected_error_fields:
                self.assertIn(field, serializer.errors)
        
        return serializer

    def assert_user_attributes(self, user, expected_data):
        """Assert user attributes match expected data"""
        for attr, value in expected_data.items():
            self.assertEqual(getattr(user, attr), value)


class UserRegistrationSerializerTests(TestCase, SerializerTestsMixin):
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
            {'email': 'test@example.com', 'username': 'testuser'}
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
        CustomUser.objects.create_user(
            username='existing',
            email='test@example.com',
            password='password123'
        )
        
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

    def test_duplicate_username(self):
        """Test duplicate username validation"""
        CustomUser.objects.create_user(
            username='testuser',
            email='existing@example.com',
            password='password123'
        )
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpassword123',
            'password_confirm': 'complexpassword123',
        }
        
        self.assert_serializer_invalid(
            UserRegistrationSerializer, 
            data, 
            ['username']
        )


class UserLoginSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for UserLoginSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/')
    
    def test_valid_login(self):
        """Test valid login"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        serializer = self.assert_serializer_valid(
            UserLoginSerializer, 
            data, 
            context={'request': self.request}
        )
        self.assertEqual(serializer.validated_data['user'], self.user)
    
    def test_invalid_credentials(self):
        """Test invalid login credentials"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        self.assert_serializer_invalid(
            UserLoginSerializer, 
            data, 
            context={'request': self.request}
        )
    
    def test_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        self.assert_serializer_invalid(
            UserLoginSerializer, 
            data, 
            context={'request': self.request}
        )

    def test_missing_fields(self):
        """Test login with missing fields"""
        data = {
            'email': 'test@example.com'
            # Password missing
        }
        
        self.assert_serializer_invalid(
            UserLoginSerializer, 
            data, 
            ['password'],
            context={'request': self.request}
        )


class UserSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for UserSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            bio='Test bio',
            location='Test City'
        )
        # UserProfile is automatically created, so we just update it
        self.user.profile.github_username = 'testgithub'
        self.user.profile.job_title = 'Developer'
        self.user.profile.save()
    
    def test_user_serialization(self):
        """Test user data serialization"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['full_name'], 'Test User')
        self.assertEqual(data['bio'], 'Test bio')
        self.assertEqual(data['location'], 'Test City')
        self.assertIn('profile', data)
        self.assertEqual(data['profile']['github_username'], 'testgithub')
        self.assertEqual(data['profile']['job_title'], 'Developer')


class PublicUserSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for PublicUserSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            bio='Test bio',
            is_profile_public=True
        )
        # UserProfile is automatically created, so we just update it
        self.user.profile.github_username = 'testgithub'
        self.user.profile.save()
    
    def test_public_profile_serialization(self):
        """Test public profile serialization"""
        serializer = PublicUserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['full_name'], 'Test User')
        self.assertEqual(data['bio'], 'Test bio')
        self.assertIn('profile', data)
        self.assertEqual(data['profile']['github_username'], 'testgithub')
    
    def test_private_profile(self):
        """Test private profile response"""
        self.user.is_profile_public = False
        self.user.save()
        
        serializer = PublicUserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data, {
            'message': 'This profile is private',
            'username': 'testuser'
        })


class UserUpdateSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for UserUpdateSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = APIRequestFactory()
    
    def test_update_user_and_profile(self):
        """Test updating user and profile data"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio',
            'profile': {
                'github_username': 'updatedgithub',
                'job_title': 'Senior Developer'
            }
        }
        
        request = self.factory.post('/')
        serializer = UserUpdateSerializer(instance=self.user, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        user = serializer.update(self.user, serializer.validated_data)
        self.user.profile.refresh_from_db()
        
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
        self.assertEqual(user.bio, 'Updated bio')
        self.assertEqual(self.user.profile.github_username, 'updatedgithub')
        self.assertEqual(self.user.profile.job_title, 'Senior Developer')

class PasswordChangeSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for PasswordChangeSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/')
        self.request.user = self.user
    
    def test_valid_password_change(self):
        """Test valid password change"""
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        serializer = self.assert_serializer_valid(
            PasswordChangeSerializer, 
            data, 
            context={'request': self.request}
        )
        
        user = serializer.save()
        self.assertTrue(user.check_password('newpass123'))
    
    def test_invalid_old_password(self):
        """Test invalid old password"""
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        self.assert_serializer_invalid(
            PasswordChangeSerializer, 
            data, 
            ['old_password'],
            context={'request': self.request}
        )
    
    def test_password_mismatch(self):
        """Test new password mismatch"""
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        
        self.assert_serializer_invalid(
            PasswordChangeSerializer, 
            data, 
            ['non_field_errors'],
            context={'request': self.request}
        )


class PasswordResetRequestSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for PasswordResetRequestSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_valid_email(self):
        """Test valid email for password reset"""
        data = {'email': 'test@example.com'}
        serializer = self.assert_serializer_valid(PasswordResetRequestSerializer, data)
        self.assertEqual(serializer.validated_data['email'], 'test@example.com')
    
    def test_nonexistent_email(self):
        """Test nonexistent email"""
        data = {'email': 'nonexistent@example.com'}
        self.assert_serializer_invalid(PasswordResetRequestSerializer, data, ['email'])


class PasswordResetConfirmSerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for PasswordResetConfirmSerializer"""
    
    def test_valid_password_reset(self):
        """Test valid password reset confirmation"""
        from uuid import uuid4
        token = uuid4()
        
        data = {
            'token': str(token),
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        serializer = self.assert_serializer_valid(PasswordResetConfirmSerializer, data)
        self.assertEqual(serializer.validated_data['new_password'], 'newpass123')
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        from uuid import uuid4
        token = uuid4()
        
        data = {
            'token': str(token),
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        
        self.assert_serializer_invalid(PasswordResetConfirmSerializer, data, ['non_field_errors'])


class UserActivitySerializerTests(TestCase, SerializerTestsMixin):
    """Test cases for UserActivitySerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.activity = UserActivity.objects.create(
            user=self.user,
            activity_type='LOGIN',
            ip_address='127.0.0.1'
        )
    
    def test_activity_serialization(self):
        """Test user activity serialization"""
        serializer = UserActivitySerializer(self.activity)
        data = serializer.data
        
        self.assertEqual(data['user'], 'test@example.com')  # Updated to match email as string representation
        self.assertEqual(data['activity_type'], 'LOGIN')
        self.assertEqual(data['ip_address'], '127.0.0.1')
        self.assertIn('timestamp', data)


class UserStatsSerializerTests(TestCase):
    """Test cases for UserStatsSerializer"""
    
    def setUp(self):
        """Set up test data for each test"""
        self.user1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
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