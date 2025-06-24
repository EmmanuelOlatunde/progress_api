# users/urls.py
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, PublicProfileView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView,
    UserViewSet, UserActivityViewSet, current_user,
    public_profiles_list, upload_avatar
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'activities', UserActivityViewSet, basename='activity')

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', current_user, name='current_user'),
    
    # Password management
    path('auth/password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Profile endpoints
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/avatar/', upload_avatar, name='upload_avatar'),
    path('profile/<str:username>/', PublicProfileView.as_view(), name='public_profile'),
    
    # Public profiles listing
    path('profiles/public/', public_profiles_list, name='public_profiles_list'),
    
    # Include router URLs for ViewSets
    path('api/', include(router.urls)),
]
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, PublicProfileView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView,
    UserViewSet, UserActivityViewSet, current_user,
    public_profiles_list, upload_avatar
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'activities', UserActivityViewSet, basename='activity')

app_name = 'users'

urlpatterns = [
    # Auth
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', current_user, name='current_user'),

    # Password
    path('auth/password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Profiles
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/avatar/', upload_avatar, name='upload_avatar'),
    path('profile/<str:username>/', PublicProfileView.as_view(), name='public_profile'),
    path('profiles/public/', public_profiles_list, name='public_profiles_list'),

    # Routers for ViewSets (users, activities)
    path('', include(router.urls)),
]
