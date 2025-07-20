
from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, PublicProfileView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView,
    UserViewSet, UserActivityViewSet, CurrentUserView,
    PublicProfilesListView, UploadAvatarView)

User = get_user_model()


class URLRoutingTests(TestCase):
    """Test URL routing and view resolution"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_auth_register_url_resolves(self):
        """Test registration URL resolves to correct view"""
        url = reverse('users:register')
        self.assertEqual(url, '/api/auth/register/')  # Changed from '/api/auth/register/'        
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, UserRegistrationView)
    
    def test_auth_login_url_resolves(self):
        """Test login URL resolves to correct view"""
        url = reverse('users:login')
        self.assertEqual(url, '/api/auth/login/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, UserLoginView)
    
    def test_auth_logout_url_resolves(self):
        """Test logout URL resolves to correct view"""
        url = reverse('users:logout')
        self.assertEqual(url, '/api/auth/logout/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, UserLogoutView)
    
    def test_token_refresh_url_resolves(self):
        """Test token refresh URL resolves correctly"""
        url = reverse('users:token_refresh')
        self.assertEqual(url, '/api/auth/token/refresh/')
        # Note: TokenRefreshView is from rest_framework_simplejwt
    
    def test_current_user_url_resolves(self):
        """Test current user URL resolves to correct view"""
        url = reverse('users:current_user')
        self.assertEqual(url, '/api/auth/me/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, CurrentUserView)
    
    def test_password_change_url_resolves(self):
        """Test password change URL resolves to correct view"""
        url = reverse('users:password_change')
        self.assertEqual(url, '/api/auth/password/change/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PasswordChangeView)
    
    def test_password_reset_url_resolves(self):
        """Test password reset URL resolves to correct view"""
        url = reverse('users:password_reset')
        self.assertEqual(url, '/api/auth/password/reset/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PasswordResetRequestView)
    
    def test_password_reset_confirm_url_resolves(self):
        """Test password reset confirm URL resolves to correct view"""
        url = reverse('users:password_reset_confirm')
        self.assertEqual(url, '/api/auth/password/reset/confirm/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PasswordResetConfirmView)
    
    def test_user_profile_url_resolves(self):
        """Test user profile URL resolves to correct view"""
        url = reverse('users:user_profile')
        self.assertEqual(url, '/api/profile/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, UserProfileView)
    
    def test_upload_avatar_url_resolves(self):
        """Test upload avatar URL resolves to correct view"""
        url = reverse('users:upload_avatar')
        self.assertEqual(url, '/api/profile/avatar/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, UploadAvatarView)
    
    def test_public_profile_url_resolves(self):
        """Test public profile URL with username parameter resolves correctly"""
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        self.assertEqual(url, '/api/profile/testuser/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PublicProfileView)
    
    def test_public_profiles_list_url_resolves(self):
        """Test public profiles list URL resolves to correct view"""
        url = reverse('users:public_profiles_list')
        self.assertEqual(url, '/api/profiles/public/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.view_class, PublicProfilesListView)


class ViewSetURLTests(TestCase):
    """Test ViewSet URL routing"""
    
    def test_user_viewset_list_url(self):
        """Test user viewset list URL"""
        url = reverse('users:user-list')
        self.assertEqual(url, '/api/users/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserViewSet)
    
    def test_user_viewset_detail_url(self):
        """Test user viewset detail URL"""
        url = reverse('users:user-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/users/1/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserViewSet)
    
    def test_user_viewset_stats_action_url(self):
        """Test user viewset stats action URL"""
        url = reverse('users:user-stats')
        self.assertEqual(url, '/api/users/stats/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserViewSet)
    
    def test_user_viewset_public_profiles_action_url(self):
        """Test user viewset public profiles action URL"""
        url = reverse('users:user-public-profiles')
        self.assertEqual(url, '/api/users/public_profiles/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserViewSet)
    
    def test_activity_viewset_list_url(self):
        """Test activity viewset list URL"""
        url = reverse('users:activity-list')
        self.assertEqual(url, '/api/activities/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserActivityViewSet)
    
    def test_activity_viewset_detail_url(self):
        """Test activity viewset detail URL"""
        url = reverse('users:activity-detail', kwargs={'pk': 1})
        self.assertEqual(url, '/api/activities/1/')
        resolver = resolve(url)
        self.assertEqual(resolver.func.cls, UserActivityViewSet)


class URLParameterValidationTests(APITestCase):
    """Test URL parameter validation and edge cases"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_public_profile_with_valid_username(self):
        """Test public profile URL with valid username"""
        url = reverse('users:public_profile', kwargs={'username': 'testuser'})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 404])  # Depends on profile visibility
    
    def test_public_profile_with_special_characters_username(self):
        """Test public profile URL with special characters in username"""
        User.objects.create_user(
            username='test-user_123',
            email='special@example.com',
            password='testpass123'
        )
        url = reverse('users:public_profile', kwargs={'username': 'test-user_123'})
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 404])
    
    def test_public_profile_with_nonexistent_username(self):
        """Test public profile URL with non-existent username"""
        url = reverse('users:public_profile', kwargs={'username': 'nonexistent'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_viewset_with_invalid_pk(self):
        """Test viewset URLs with invalid primary key"""
        # Create admin user for access
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        refresh = RefreshToken.for_user(admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('users:user-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_viewset_with_string_pk(self):
        """Test viewset URLs with string primary key (should fail)"""
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        refresh = RefreshToken.for_user(admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = '/api/users/invalid/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class URLAccessPatternTests(APITestCase):
    """Test different access patterns for URLs"""
    
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
    
    def test_anonymous_access_patterns(self):
        """Test URLs accessible to anonymous users"""
        anonymous_urls = [
            ('users:register', {}),
            ('users:login', {}),
            ('users:token_refresh', {}),
            ('users:password_reset', {}),
            ('users:password_reset_confirm', {}),
            ('users:public_profile', {'username': 'testuser'}),
            ('users:public_profiles_list', {}),
        ]
        
        for url_name, kwargs in anonymous_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url) if 'GET' in self._get_allowed_methods(url_name) else self.client.post(url, {})
            self.assertNotEqual(response.status_code, 403, f"URL {url_name} should be accessible to anonymous users")
    
    def test_authenticated_only_urls(self):
        """Test URLs that require authentication"""
        auth_required_urls = [
            ('users:logout', {}),
            ('users:current_user', {}),
            ('users:password_change', {}),
            ('users:user_profile', {}),
            ('users:upload_avatar', {}),
            ('users:activity-list', {}),
        ]
        
        # Test without authentication
        for url_name, kwargs in auth_required_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url) if 'GET' in self._get_allowed_methods(url_name) else self.client.post(url, {})
            self.assertEqual(response.status_code, 401, f"URL {url_name} should require authentication")
        
        # Test with authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        for url_name, kwargs in auth_required_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url) if 'GET' in self._get_allowed_methods(url_name) else self.client.post(url, {})
            self.assertNotEqual(response.status_code, 401, f"URL {url_name} should be accessible to authenticated users")
    
    def test_admin_only_urls(self):
        """Test URLs that require admin privileges"""
        admin_urls = [
            ('users:user-list', {}),
            ('users:user-detail', {'pk': 1}),
            ('users:user-stats', {}),
            ('users:user-public-profiles', {}),
        ]
        
        # Test without authentication
        for url_name, kwargs in admin_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, f"URL {url_name} should require authentication")
        
        # Test with regular user
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        for url_name, kwargs in admin_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"URL {url_name} should require admin privileges")
        
        # Test with admin user
        admin_refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_refresh.access_token}')
        
        for url_name, kwargs in admin_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertIn(response.status_code, [200, 404], f"URL {url_name} should be accessible to admin users")
    
    def _get_allowed_methods(self, url_name):
        """Helper method to determine allowed HTTP methods for a URL"""
        get_urls = [
            'current_user', 'user_profile', 'public_profile', 'public_profiles_list',
            'user-list', 'user-detail', 'user-stats', 'user-public-profiles',
            'activity-list', 'activity-detail'
        ]
        
        if any(get_url in url_name for get_url in get_urls):
            return ['GET']
        return ['POST']


class URLNamespaceTests(TestCase):
    """Test URL namespacing"""
    
    def test_app_namespace(self):
        """Test that all URLs are properly namespaced"""
        # Test that namespace is required
        with self.assertRaises(Exception):
            reverse('register')  # Should fail without namespace
        
        # Test that namespaced URLs work
        url = reverse('users:register')
        self.assertIsNotNone(url)
    
    def test_all_named_urls_resolvable(self):
        """Test that all named URLs in urlpatterns are resolvable"""
        url_names = [
            'register', 'login', 'logout', 'token_refresh', 'current_user',
            'password_change', 'password_reset', 'password_reset_confirm',
            'user_profile', 'upload_avatar', 'public_profiles_list',
            'user-list', 'user-detail', 'user-stats', 'user-public-profiles',
            'activity-list', 'activity-detail'
        ]
        
        for url_name in url_names:
            try:
                if url_name in ['public_profile']:
                    url = reverse(f'users:{url_name}', kwargs={'username': 'test'})
                elif url_name in ['user-detail', 'activity-detail']:
                    url = reverse(f'users:{url_name}', kwargs={'pk': 1})
                else:
                    url = reverse(f'users:{url_name}')
                self.assertIsNotNone(url)
            except Exception as e:
                self.fail(f"URL {url_name} should be resolvable: {e}")


class URLQueryParameterTests(APITestCase):
    """Test URL query parameter handling"""
    
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
    
    def test_public_profiles_with_search_parameter(self):
        """Test public profiles list with search query parameter"""
        url = reverse('users:public_profiles_list')
        response = self.client.get(url, {'search': 'test'})
        self.assertEqual(response.status_code, 200)
    
    def test_public_profiles_with_experience_filter(self):
        """Test public profiles list with experience filter"""
        url = reverse('users:public_profiles_list')
        response = self.client.get(url, {'experience': 'senior'})
        self.assertEqual(response.status_code, 200)
    
    def test_public_profiles_with_pagination(self):
        """Test public profiles list with pagination parameters"""
        url = reverse('users:public_profiles_list')
        response = self.client.get(url, {'page': '1'})
        self.assertEqual(response.status_code, 200)
    
    def test_public_profiles_with_multiple_parameters(self):
        """Test public profiles list with multiple query parameters"""
        url = reverse('users:public_profiles_list')
        response = self.client.get(url, {
            'search': 'test',
            'experience': 'senior',
            'page': '1'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_viewset_filtering_with_authenticated_user(self):
        """Test ViewSet filtering with authenticated admin user"""
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        refresh = RefreshToken.for_user(admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('users:user-list')
        response = self.client.get(url, {'is_active': 'true'})
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(url, {'search': 'test'})
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(url, {'ordering': '-date_joined'})
        self.assertEqual(response.status_code, 200)