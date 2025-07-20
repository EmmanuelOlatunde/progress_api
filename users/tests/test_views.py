"""
Comprehensive test suite for users app views
Tests all view functionality, permissions, error handling, and edge cases
The below is my test file the above 2 are the missing test
Generate the code for missing test and other test Comprehensive test suite for users app views Tests all view functionality, permissions, error handling, and edge cases.

Dont rewrite anything that is the test_views.py again
"""

from datetime import timedelta
from io import BytesIO
from PIL import Image
from unittest.mock import patch, MagicMock
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
# from django.test import override_settings
# from concurrent.futures import ThreadPoolExecutor

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import UserActivity, PasswordResetToken
from users.views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    PasswordResetRequestView, UploadAvatarView
)

User = get_user_model()


class UserRegistrationViewTests(APITestCase):
    """Test UserRegistrationView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:register')
    
    def test_successful_registration(self):
        """Test successful user registration"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'complexpass123',
            'password_confirm': 'complexpass123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+1234567890'
        }
        response = self.client.post(self.url, data)
        print(response.data)  # Debug output to inspect errors
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Account created successfully. Please check your email for verification.')
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        activity = UserActivity.objects.get(user=user, activity_type='registration')
        self.assertIsNotNone(activity)

    def test_registration_with_duplicate_username(self):
        """Test registration with existing username"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password123'
        )
        
        data = {
            'username': 'existing',
            'email': 'different@example.com',
            'password': 'complexpass123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_with_duplicate_email(self):
        """Test registration with existing email"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password123'
        )
        
        data = {
            'username': 'different',
            'email': 'existing@example.com',
            'password': 'complexpass123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_with_invalid_data(self):
        """Test registration with invalid data"""
        data = {
            'username': '',
            'email': 'invalid-email',
            'password': '123'  # Too short
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_missing_required_fields(self):
        """Test registration with missing required fields"""
        data = {'username': 'newuser'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('users.views.UserRegistrationView.get_client_ip')
    def test_get_client_ip_with_forwarded_header(self, mock_get_ip):
        """Test IP extraction with X-Forwarded-For header"""
        mock_get_ip.return_value = '192.168.1.1'
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'complexpass123'
        }
        
        with patch.object(self.client, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = status.HTTP_201_CREATED
            mock_response.data = {'message': 'Account created successfully. Please check your email for verification.'}
            mock_post.return_value = mock_response
            
            self.client.post(self.url, data, HTTP_X_FORWARDED_FOR='192.168.1.1,10.0.0.1')
            
    def test_get_client_ip_method_with_forwarded_header(self):
        """Test the actual get_client_ip method with forwarded header"""
        view = UserRegistrationView()
        
        # Mock request with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1,10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        view.request = mock_request
        
        ip = view.get_client_ip()
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_method_without_forwarded_header(self):
        """Test the actual get_client_ip method without forwarded header"""
        view = UserRegistrationView()
        
        # Mock request without X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.META = {'REMOTE_ADDR': '127.0.0.1'}
        view.request = mock_request
        
        ip = view.get_client_ip()
        self.assertEqual(ip, '127.0.0.1')


class UserLoginViewTests(APITestCase):
    """Test UserLoginView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    # def test_successful_login_with_username(self):
    #     """Test successful login with username"""
    #     data = {
    #         'username': 'testuser',
    #         'password': 'testpass123'
    #     }
    #     response = self.client.post(self.url, data)
        
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertIn('access', response.data)
    #     self.assertIn('refresh', response.data)
    #     self.assertIn('user', response.data)
    #     self.assertEqual(response.data['message'], 'Login successful')
        
    #     # Verify activity was logged
    #     activity = UserActivity.objects.get(user=self.user, activity_type='login')
    #     self.assertIsNotNone(activity)
        
    #     # Verify last login was updated
    #     self.user.refresh_from_db()
    #     self.assertIsNotNone(self.user.last_login)
    
    def test_successful_login_with_email(self):
        """Test successful login with email"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_login_with_wrong_password(self):
        """Test login with incorrect password"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_with_nonexistent_user(self):
        """Test login with non-existent username"""
        data = {
            'email': 'test12211@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_with_inactive_user(self):
        """Test login with inactive user account"""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_missing_credentials(self):
        """Test login with missing credentials"""
        data = {'email': 'test@example.com',}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_client_ip_method(self):
        """Test the get_client_ip method"""
        view = UserLoginView()
        
        # Mock request with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1,10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        view.request = mock_request
        
        ip = view.get_client_ip()
        self.assertEqual(ip, '192.168.1.1')


class UserLogoutViewTests(APITestCase):
    """Test UserLogoutView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:logout')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def test_successful_logout(self):
        """Test successful logout with token blacklisting"""
        data = {'refresh_token': str(self.refresh)}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logout successful')
        
        # Verify activity was logged
        activity = UserActivity.objects.get(user=self.user, activity_type='logout')
        self.assertIsNotNone(activity)
    
    def test_logout_without_refresh_token(self):
        """Test logout without providing refresh token"""
        data = {}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logout successful')
    
    def test_logout_with_invalid_token(self):
        """Test logout with invalid refresh token"""
        data = {'refresh_token': 'invalid_token'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_logout_without_authentication(self):
        """Test logout without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_client_ip_method(self):
        """Test the get_client_ip method"""
        view = UserLogoutView()
        
        # Mock request
        mock_request = MagicMock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1,10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        ip = view.get_client_ip(mock_request)
        self.assertEqual(ip, '192.168.1.1')


class UserProfileViewTests(APITestCase):
    """Test UserProfileView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:user_profile')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def test_get_user_profile(self):
        """Test retrieving user profile"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
        response = self.client.get(self.url)
        print(response.data)  # Debug output to inspect response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email_notifications'], True)  # Default value
        self.assertIsNotNone(response.data['profile'])
        
    def test_update_user_profile_patch(self):
        """Test partial update of user profile"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.patch(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        
        # Verify activity was logged
        activity = UserActivity.objects.get(user=self.user, activity_type='profile_update')
        self.assertIsNotNone(activity)
    
    def test_update_user_profile_put(self):
        """Test full update of user profile"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Completely',
            'last_name': 'Updated',
            'is_profile_public': True
        }
        response = self.client.put(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Completely')
        self.assertEqual(self.user.last_name, 'Updated')
    
    def test_profile_access_without_authentication(self):
        """Test profile access without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_with_invalid_data(self):
        """Test profile update with invalid data"""
        data = {
            'email': 'invalid-email-format'
        }
        response = self.client.patch(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('users.models.UserProfile.calculate_completeness', return_value=None)
    def test_profile_completeness_calculation_called(self, mock_calculate):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'first_name': 'Updated'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_calculate.call_count, 2)

class PublicProfileViewTests(APITestCase):
    """Test PublicProfileView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.user.is_profile_public = True
        self.user.save()
        
        self.private_user = User.objects.create_user(
            username='private_user',
            email='private@example.com',
            password='testpass123'
        )
        self.private_user.is_profile_public = False
        self.private_user.save()
    
    def test_view_public_profile(self):
        """Test viewing a public profile"""
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_view_private_profile(self):
        """Test viewing a private profile"""
        url = reverse('users:public_profile', kwargs={'username': 'private_user'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Profile should still be returned but might have limited info
    
    def test_view_nonexistent_profile(self):
        """Test viewing non-existent profile"""
        url = reverse('users:public_profile', kwargs={'username': 'nonexistent'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('users.models.UserProfile.increment_profile_views')
    def test_profile_view_increment_for_public_profile(self, mock_increment):
        """Test that profile views are incremented for public profiles"""
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_increment.assert_called_once()
    
    @patch('users.models.UserProfile.increment_profile_views')
    def test_profile_view_not_incremented_for_private_profile(self, mock_increment):
        """Test that profile views are not incremented for private profiles"""
        url = reverse('users:public_profile', kwargs={'username': 'private_user'})
        self.client.get(url)
        
        mock_increment.assert_not_called()
    
    def test_profile_view_activity_logged_for_authenticated_user(self):
        """Test that profile view activity is logged for authenticated users"""
        viewer = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123'
        )
        refresh = RefreshToken.for_user(viewer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify activity was logged
        activity = UserActivity.objects.filter(user=viewer, activity_type='profile_view')
        self.assertTrue(activity.exists())
    
    def test_profile_view_activity_not_logged_for_self_view(self):
        """Test that profile view activity is not logged when viewing own profile"""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify no activity was logged for self-view
        activity = UserActivity.objects.filter(user=self.user, activity_type='profile_view')
        self.assertFalse(activity.exists())


class PasswordChangeViewTests(APITestCase):
    """Test PasswordChangeView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:password_change')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def test_successful_password_change(self):
        """Test successful password change"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password changed successfully')
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))
        
        # Verify activity was logged
        activity = UserActivity.objects.get(user=self.user, activity_type='password_change')
        self.assertIsNotNone(activity)
    
    def test_password_change_with_wrong_old_password(self):
        """Test password change with incorrect old password"""
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_change_with_mismatched_passwords(self):
        """Test password change with mismatched new passwords"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'differentpass'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_change_without_authentication(self):
        """Test password change without authentication"""
        self.client.credentials()  # Remove authentication
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_password_change_with_weak_password(self):
        """Test password change with weak new password"""
        data = {
            'old_password': 'oldpass123',
            'new_password': '123',
            'new_password_confirm': '123'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestViewTests(APITestCase):
    """Test PasswordResetRequestView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:password_reset')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_successful_password_reset_request(self):
        """Test successful password reset request"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password reset instructions sent to your email')
        
        # Verify reset token was created
        reset_token = PasswordResetToken.objects.get(user=self.user)
        self.assertIsNotNone(reset_token)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset Request', mail.outbox[0].subject)
    
    def test_password_reset_request_nonexistent_email(self):
        """Test password reset request with non-existent email"""
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email format"""
        data = {'email': 'invalid-email'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_reset_request_missing_email(self):
        """Test password reset request without email"""
        data = {}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('users.views.PasswordResetRequestView.send_reset_email')
    def test_send_reset_email_called(self, mock_send_email):
        """Test that send_reset_email method is called"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()
    
    def test_send_reset_email_method(self):
        """Test the send_reset_email method directly"""
        view = PasswordResetRequestView()
        token = 'test-token-123'
        
        with patch('users.views.send_mail') as mock_send_mail:
            view.send_reset_email(self.user, token)
            
            mock_send_mail.assert_called_once()
            args, kwargs = mock_send_mail.call_args
            self.assertIn('Password Reset Request', args[0])
            self.assertIn(token, args[1])
            self.assertEqual(args[3], [self.user.email])


class PasswordResetConfirmViewTests(APITestCase):
    """Test PasswordResetConfirmView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:password_reset_confirm')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )
        self.reset_token = PasswordResetToken.objects.create(
            user=self.user,
            ip_address='127.0.0.1'
        )
    
    def test_successful_password_reset_confirm(self):
        """Test successful password reset confirmation"""
        data = {
            'token': str(self.reset_token.token),
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password reset successful')
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))
        
        # Verify token was marked as used
        self.reset_token.refresh_from_db()
        self.assertTrue(self.reset_token.is_used)
        
        # Verify activity was logged
        activity = UserActivity.objects.get(user=self.user, activity_type='password_reset')
        self.assertIsNotNone(activity)
    
    def test_password_reset_with_invalid_token(self):
        """Test password reset with invalid token"""
        data = {
            'token': str(uuid.uuid4()),
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid token')
    
    def test_password_reset_with_malformed_token(self):
        data = {
            'token': 'abc123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Must be a valid UUID', str(response.data['token']))

    def test_password_reset_with_expired_token(self):
        """Test password reset with expired token"""
        # Force token expiration
        self.reset_token.expires_at = timezone.now() - timedelta(hours=1)
        self.reset_token.save()

        data = {
            'token': str(self.reset_token.token),
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'])

    def test_password_reset_with_used_token(self):
        """Test password reset with already used token"""
        self.reset_token.is_used = True
        self.reset_token.save()
        
        data = {
            'token': str(self.reset_token.token),
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'])
    
    def test_password_reset_with_mismatched_passwords(self):
        """Test password reset with mismatched passwords"""
        data = {
            'token': str(self.reset_token.token),
            'new_password': 'newpass456',
            'new_password_confirm': 'differentpass'
        }
        response = self.client.post(self.url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserViewSetTests(APITestCase):
    """Test UserViewSet functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123'
        )
        
        self.admin_refresh = RefreshToken.for_user(self.admin_user)
        self.user_refresh = RefreshToken.for_user(self.regular_user)
    
    def test_admin_can_list_users(self):
        """Test admin can list all users"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_refresh.access_token}')
        url = reverse('users:user-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)  # At least admin and regular user
    
    def test_regular_user_cannot_list_users(self):
        """Test regular user cannot list users"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_refresh.access_token}')
        url = reverse('users:user-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthenticated_cannot_list_users(self):
        """Test unauthenticated user cannot list users"""
        url = reverse('users:user-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_can_get_user_detail(self):
        """Test admin can get user details"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_refresh.access_token}')
        url = reverse('users:user-detail', kwargs={'pk': self.regular_user.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'user')
    
    def test_user_stats_action(self):
        """Test user stats action"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_refresh.access_token}')
        url = reverse('users:user-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Stats should contain user counts and other metrics
    
    def test_public_profiles_action(self):
        """Test public profiles action"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_refresh.access_token}')
        
        # Make regular user profile public
        self.regular_user.is_profile_public = True
        self.regular_user.save()
        
        url = reverse('users:user-public-profiles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_user_filtering(self):
        """Test user filtering functionality"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_refresh.access_token}')
        url = reverse('users:user-list')
        
        # Test filtering by is_active
        response = self.client.get(url, {'is_active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test search
        response = self.client.get(url, {'search': 'user'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test ordering
        response = self.client.get(url, {'ordering': '-date_joined'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserActivityViewSetTests(APITestCase):
    """Test UserActivityViewSet functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create some activities
        UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            ip_address='127.0.0.1'
        )
        UserActivity.objects.create(
            user=self.user,
            activity_type='profile_update',
            ip_address='127.0.0.1'
        )
        UserActivity.objects.create(
            user=self.other_user,
            activity_type='login',
            ip_address='127.0.0.1'
        )
        
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def test_user_can_list_own_activities(self):
        """Test user can list their own activities"""
        url = reverse('users:activity-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        for activity in response.data['results']:
            self.assertEqual(activity['user'], self.user.email)

    
    def test_user_cannot_see_others_activities(self):
        """Test user cannot see other users' activities"""
        url = reverse('users:activity-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify no activities from other_user are returned
        user_ids = [activity['user'] for activity in response.data['results']]
        self.assertNotIn(self.other_user.pk, user_ids)
    
    def test_activity_filtering(self):
        """Test activity filtering by type"""
        url = reverse('users:activity-list')
        response = self.client.get(url, {'activity_type': 'login'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['activity_type'], 'login')
    
    def test_unauthenticated_cannot_list_activities(self):
        """Test unauthenticated user cannot list activities"""
        self.client.credentials()  # Remove authentication
        url = reverse('users:activity-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentUserViewTests(APITestCase):
    """Test CurrentUserView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:current_user')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def test_get_current_user_details(self):
        """Test getting current authenticated user details"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
    
    def test_current_user_without_authentication(self):
        """Test getting current user without authentication"""
        self.client.credentials()  # Remove authentication
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PublicProfilesListViewTests(APITestCase):
    """Test PublicProfilesListView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:public_profiles_list')
        
        # Create public users
        self.public_user1 = User.objects.create_user(
            username='public1',
            email='public1@example.com',
            password='testpass123',
            first_name='Public',
            last_name='User1'
        )
        self.public_user1.is_profile_public = True
        self.public_user1.save()
        
        self.public_user2 = User.objects.create_user(
            username='public2',
            email='public2@example.com',
            password='testpass123',
            first_name='Public',
            last_name='User2'
        )
        self.public_user2.is_profile_public = True
        self.public_user2.save()
        
        # Create private user
        self.private_user = User.objects.create_user(
            username='private1',
            email='private@example.com',
            password='testpass123'
        )
        self.private_user.is_profile_public = False
        self.private_user.save()
    
    def test_list_public_profiles(self):
        """Test listing all public profiles"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)
        
        # Verify only public users are returned
        usernames = [user['username'] for user in response.data['results']]
        self.assertIn('public1', usernames)
        self.assertIn('public2', usernames)
        self.assertNotIn('private1', usernames)
    
    def test_search_public_profiles(self):
        """Test searching public profiles"""
        response = self.client.get(self.url, {'search': 'public1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')
    
    def test_search_by_name(self):
        """Test searching by first/last name"""
        response = self.client.get(self.url, {'search': 'User1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')
    
    def test_filter_by_experience(self):
        """Test filtering by experience level"""
        # Set experience levels for testing
        self.public_user1.profile.experience_level = 'senior'
        self.public_user1.profile.save()
        
        self.public_user2.profile.experience_level = 'junior'
        self.public_user2.profile.save()
        
        response = self.client.get(self.url, {'experience': 'senior'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')
    
    def test_pagination(self):
        """Test pagination functionality"""
        # Create additional public users to test pagination
        for i in range(15):
            user = User.objects.create_user(
                username=f'public_user_{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            user.is_profile_public = True
            user.save()
        
        # Test first page
        response = self.client.get(self.url, {'page': 1})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 12)  # 12 per page
        self.assertEqual(response.data['count'], 17)  # 2 original + 15 new
        self.assertEqual(response.data['num_pages'], 2)
        self.assertEqual(response.data['current_page'], 1)
        self.assertTrue(response.data['has_next'])
        self.assertFalse(response.data['has_previous'])
        
        # Test second page
        response = self.client.get(self.url, {'page': 2})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # Remaining users
        self.assertEqual(response.data['current_page'], 2)
        self.assertFalse(response.data['has_next'])
        self.assertTrue(response.data['has_previous'])
    
    def test_search_by_job_title(self):
        """Test searching by job title"""
        self.public_user1.profile.job_title = 'Software Engineer'
        self.public_user1.profile.save()
        
        self.public_user2.profile.job_title = 'Data Scientist'
        self.public_user2.profile.save()
        
        response = self.client.get(self.url, {'search': 'Engineer'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')
    
    def test_search_by_skills(self):
        """Test searching by skills"""
        self.public_user1.profile.skills = 'Python, Django, React'
        self.public_user1.profile.save()
        
        self.public_user2.profile.skills = 'Java, Spring, Angular'
        self.public_user2.profile.save()
        
        response = self.client.get(self.url, {'search': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')
    
    def test_empty_search_results(self):
        """Test search with no matching results"""
        response = self.client.get(self.url, {'search': 'nonexistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['count'], 0)
    
    def test_invalid_page_number(self):
        """Test with invalid page number"""
        response = self.client.get(self.url, {'page': 999})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return the last page
    
    def test_no_public_profiles(self):
        """Test when no public profiles exist"""
        # Make all users private
        User.objects.filter(is_profile_public=True).update(is_profile_public=False)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['count'], 0)
    
    def test_multiple_filters_combined(self):
        """Test combining search and experience filter"""
        self.public_user1.profile.experience_level = 'senior'
        self.public_user1.profile.save()
        
        self.public_user2.profile.experience_level = 'senior'
        self.public_user2.profile.save()
        
        response = self.client.get(self.url, {
            'search': 'public1',
            'experience': 'senior'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'public1')


class UploadAvatarViewTests(APITestCase):
    """Test UploadAvatarView functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:upload_avatar')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
    def create_test_image(self, format='JPEG', size=(100, 100), file_size_mb=1):
        """Helper method to create test image files"""
        image = Image.new('RGB', size, color='red')
        file_obj = BytesIO()
        image.save(file_obj, format=format)
        file_obj.seek(0)
        
        # Adjust file size if needed
        if format == 'JPEG':
            content_type = 'image/jpeg'
            filename = 'test.jpg'
        elif format == 'PNG':
            content_type = 'image/png'
            filename = 'test.png'
        elif format == 'GIF':
            content_type = 'image/gif'
            filename = 'test.gif'
        else:
            content_type = 'image/webp'
            filename = 'test.webp'
        
        return SimpleUploadedFile(
            name=filename,
            content=file_obj.getvalue(),
            content_type=content_type
        )
    
    def test_successful_avatar_upload_jpeg(self):
        """Test successful JPEG avatar upload"""
        avatar_file = self.create_test_image(format='JPEG')
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Avatar uploaded successfully')
        self.assertIn('avatar_url', response.data)
        
        # Verify user avatar was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        
        # Verify activity was logged
        activity = UserActivity.objects.get(user=self.user, activity_type='avatar_update')
        self.assertIsNotNone(activity)
    
    def test_successful_avatar_upload_png(self):
        """Test successful PNG avatar upload"""
        avatar_file = self.create_test_image(format='PNG')
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Avatar uploaded successfully')
    
    def test_successful_avatar_upload_gif(self):
        """Test successful GIF avatar upload"""
        avatar_file = self.create_test_image(format='GIF')
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Avatar uploaded successfully')
    
    def test_successful_avatar_upload_webp(self):
        """Test successful WebP avatar upload"""
        # Create a simple WebP-like file
        file_obj = BytesIO(b'RIFF\x00\x00\x00\x00WEBP')
        avatar_file = SimpleUploadedFile(
            name='test.webp',
            content=file_obj.getvalue(),
            content_type='image/webp'
        )
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_upload_without_file(self):
        """Test upload request without avatar file"""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'No avatar file provided')
    
    def test_upload_file_too_large(self):
        """Test upload with file larger than 5MB"""
        # Create a large file by repeating content
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        avatar_file = SimpleUploadedFile(
            name='large.jpg',
            content=large_content,
            content_type='image/jpeg'
        )
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Avatar file too large. Max size is 5MB')
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type"""
        # Create a text file disguised as image
        avatar_file = SimpleUploadedFile(
            name='fake.txt',
            content=b'This is not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['error'], 
            'Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image'
        )
    
    def test_upload_without_authentication(self):
        """Test avatar upload without authentication"""
        self.client.credentials()  # Remove authentication
        
        avatar_file = self.create_test_image()
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_upload_replaces_existing_avatar(self):
        """Test that new avatar replaces existing one"""
        # Upload first avatar
        avatar_file1 = self.create_test_image()
        response1 = self.client.post(self.url, {'avatar': avatar_file1})
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        first_avatar_url = response1.data['avatar_url']
        
        # Upload second avatar
        avatar_file2 = self.create_test_image(format='PNG')
        response2 = self.client.post(self.url, {'avatar': avatar_file2})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        second_avatar_url = response2.data['avatar_url']
        
        # Verify the avatar was replaced
        self.assertNotEqual(first_avatar_url, second_avatar_url)
        
        # Verify multiple activities were logged
        activities = UserActivity.objects.filter(user=self.user, activity_type='avatar_update')
        self.assertEqual(activities.count(), 2)
    
    def test_get_client_ip_method(self):
        """Test the get_client_ip method"""
        view = UploadAvatarView()
        
        # Mock request with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1,10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        ip = view.get_client_ip(mock_request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test without X-Forwarded-For header
        mock_request.META = {'REMOTE_ADDR': '127.0.0.1'}
        ip = view.get_client_ip(mock_request)
        self.assertEqual(ip, '127.0.0.1')
    
    @patch('users.models.CustomUser.get_avatar_url')
    def test_get_avatar_url_called(self, mock_get_avatar_url):
        """Test that get_avatar_url method is called after successful upload"""
        mock_get_avatar_url.return_value = 'http://example.com/avatar.jpg'
        
        avatar_file = self.create_test_image()
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_avatar_url.assert_called_once()
        self.assertEqual(response.data['avatar_url'], 'http://example.com/avatar.jpg')
    
    def test_avatar_upload_activity_ip_logging(self):
        """Test that IP address is correctly logged in activity"""
        avatar_file = self.create_test_image()
        
        # Make request with custom IP
        response = self.client.post(
            self.url, 
            {'avatar': avatar_file},
            HTTP_X_FORWARDED_FOR='192.168.1.100'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that activity logged the correct IP
        activity = UserActivity.objects.get(user=self.user, activity_type='avatar_update')
        self.assertEqual(activity.ip_address, '192.168.1.100')
    
    def test_avatar_upload_activity_user_agent_logging(self):
        """Test that user agent is correctly logged in activity"""
        avatar_file = self.create_test_image()
        
        test_user_agent = 'TestBrowser/1.0'
        response = self.client.post(
            self.url,
            {'avatar': avatar_file},
            HTTP_USER_AGENT=test_user_agent
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that activity logged the correct user agent
        activity = UserActivity.objects.get(user=self.user, activity_type='avatar_update')
        self.assertEqual(activity.user_agent, test_user_agent)
    
    def test_upload_edge_case_exact_5mb_file(self):
        """Test upload with file exactly 5MB"""
        # Create exactly 5MB file
        exactly_5mb = b'x' * (5 * 1024 * 1024)
        avatar_file = SimpleUploadedFile(
            name='exactly5mb.jpg',
            content=exactly_5mb,
            content_type='image/jpeg'
        )
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        # Should succeed as it's exactly at the limit
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_upload_corrupted_image_file(self):
        """Test upload with corrupted image file"""
        # Create a file with image extension but corrupted content
        corrupted_content = b'JPEG\x00\x00corrupted'
        avatar_file = SimpleUploadedFile(
            name='corrupted.jpg',
            content=corrupted_content,
            content_type='image/jpeg'
        )
        
        response = self.client.post(self.url, {'avatar': avatar_file})
        
        # Should still accept as we're only checking content type and size
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Additional integration tests
class ViewsIntegrationTests(APITestCase):
    """Integration tests for multiple views working together"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123',
            first_name='Integration',
            last_name='Test'
        )

    def test_registration_to_profile_workflow(self):
        """Test complete workflow from registration to profile management"""
        register_url = reverse('users:register')
        register_data = {
            'username': 'newintegrationuser',
            'email': 'newintegration@example.com',
            'password': 'ComplexPass123!',
            'password_confirm': 'ComplexPass123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+1234567890'
        }
        register_response = self.client.post(register_url, register_data)
        print(register_response.data)  # Debug output
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # Login
        login_url = reverse('users:login')
        login_data = {
            'email': 'newintegration@example.com',
            'password': 'ComplexPass123!'
        }
        login_response = self.client.post(login_url, login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Set authentication
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Update profile
        profile_url = reverse('users:user_profile')
        profile_data = {'first_name': 'Updated', 'is_profile_public': True}
        profile_response = self.client.patch(profile_url, profile_data)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        
        # Check current user
        current_user_url = reverse('users:current_user')
        current_response = self.client.get(current_user_url)
        self.assertEqual(current_response.status_code, status.HTTP_200_OK)
        self.assertEqual(current_response.data['first_name'], 'Updated')
        
        # Verify profile appears in public list
        public_list_url = reverse('users:public_profiles_list')
        public_response = self.client.get(public_list_url)
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        usernames = [user['username'] for user in public_response.data['results']]
        self.assertIn('newintegrationuser', usernames)

    def test_activity_logging_across_views(self):
        """Test that activities are logged across different views"""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Perform various actions
        login_url = reverse('users:login')
        self.client.post(login_url, {'email': 'newintegration@example.com', 'password': 'testpass123'})
        
        profile_url = reverse('users:user_profile')
        self.client.patch(profile_url, {'first_name': 'ActivityTest'})
        
        password_change_url = reverse('users:password_change')
        self.client.post(password_change_url, {
            'old_password': 'testpass123',
            'new_password': 'newpass456',
            'new_password_confirm': 'newpass456'
        })
        
        # Check activities were logged
        activity_url = reverse('users:activity-list')
        activity_response = self.client.get(activity_url)
        
        self.assertEqual(activity_response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(activity_response.data['results']), 0)
        
        activity_types = [activity['activity_type'] for activity in activity_response.data['results']]
        self.assertIn('profile_update', activity_types)
        self.assertIn('password_change', activity_types)


# class RateLimitingTests(APITestCase):
#     """Test rate limiting on sensitive endpoints"""
    
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
    
#     @override_settings(RATELIMIT_LOGIN_ATTEMPTS='5/minute')
#     def test_login_rate_limiting(self):
#         """Test rate limiting on login endpoint"""
#         login_url = reverse('users:login')
#         data = {'email': 'test@example.com', 'password': 'wrongpass'}
        
#         # Make 6 login attempts
#         for _ in range(5):
#             response = self.client.post(login_url, data)
#             self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
#         # 6th attempt should be rate-limited
#         response = self.client.post(login_url, data)
#         self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
    
#     @override_settings(RATELIMIT_PASSWORD_RESET_ATTEMPTS='3/minute')
#     def test_password_reset_rate_limiting(self):
#         """Test rate limiting on password reset request"""
#         reset_url = reverse('users:password_reset')
#         data = {'email': 'test@example.com'}
        
#         for _ in range(3):
#             response = self.client.post(reset_url, data)
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
        
#         response = self.client.post(reset_url, data)
#         self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

# class ConcurrentAccessTests(APITestCase):
#     """Test concurrent access to views"""
    
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
#         self.refresh = RefreshToken.for_user(self.user)
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
#     def test_concurrent_profile_updates(self):
#         """Test concurrent profile updates"""
#         profile_url = reverse('users:user_profile')
        
#         def update_profile(client, first_name):
#             client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
#             return client.patch(profile_url, {'first_name': first_name})
        
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             clients = [APIClient() for _ in range(3)]
#             futures = [
#                 executor.submit(update_profile, client, f'Name{i}')
#                 for i, client in enumerate(clients)
#             ]
#             results = [f.result() for f in futures]
        
#         for response in results:
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
        
#         self.user.refresh_from_db()
#         # Verify one of the updates was applied
#         self.assertIn(self.user.first_name, ['Name0', 'Name1', 'Name2'])
    
#     def test_concurrent_avatar_uploads(self):
#         """Test concurrent avatar uploads"""
#         upload_url = reverse('users:upload_avatar')
        
#         def upload_avatar(client, filename):
#             client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
#             image = Image.new('RGB', (100, 100), color='red')
#             file_obj = BytesIO()
#             image.save(file_obj, format='JPEG')
#             file_obj.seek(0)
#             avatar_file = SimpleUploadedFile(
#                 name=filename,
#                 content=file_obj.getvalue(),
#                 content_type='image/jpeg'
#             )
#             return client.post(upload_url, {'avatar': avatar_file})
        
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             clients = [APIClient() for _ in range(3)]
#             futures = [
#                 executor.submit(upload_avatar, client, f'test{i}.jpg')
#                 for i, client in enumerate(clients)
#             ]
#             results = [f.result() for f in futures]
        
#         for response in results:
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
        
#         # Verify avatar was updated
#         self.user.refresh_from_db()
#         self.assertTrue(self.user.avatar)

# class AdditionalAvatarUploadTests(APITestCase):
#     """Additional edge case tests for avatar upload"""
    
#     def setUp(self):
#         self.client = APIClient()
#         self.url = reverse('users:upload_avatar')
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
#         self.refresh = RefreshToken.for_user(self.user)
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
    
#     def test_upload_empty_file(self):
#         """Test uploading an empty file"""
#         avatar_file = SimpleUploadedFile(
#             name='empty.jpg',
#             content=b'',
#             content_type='image/jpeg'
#         )
#         response = self.client.post(self.url, {'avatar': avatar_file})
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertIn('empty', response.data['error'].lower())
    
#     def test_upload_malformed_image(self):
#         """Test uploading a malformed image file"""
#         avatar_file = SimpleUploadedFile(
#             name='malformed.jpg',
#             content=b'not-an-image',
#             content_type='image/jpeg'
#         )
#         response = self.client.post(self.url, {'avatar': avatar_file})
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('error', response.data)
#         self.assertIn('invalid', response.data['error'].lower())

class PermissionTests(APITestCase):
    """Test permission edge cases"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
    
    def test_regular_user_cannot_access_admin_views(self):
        """Test regular user cannot access UserViewSet"""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        url = reverse('users:user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_access_user_activity(self):
        """Test admin can access any user's activity"""
        UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            ip_address='127.0.0.1'
        )

        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        url = reverse('users:activity-list')
        response = self.client.get(url)
        results = response.data['results']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(results), 1)  # Admin sees regular user's activity
        self.assertEqual(results[0]['user'], self.user.email)