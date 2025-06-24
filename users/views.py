from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView #TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
#from django.contrib.auth import authenticate, login, logout
#from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
#from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
#import uuid

from .models import CustomUser, UserActivity, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    PublicUserSerializer, UserUpdateSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    UserActivitySerializer, UserStatsSerializer
)

class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    POST /api/auth/register/
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        user = serializer.save()
        # Log registration activity
        UserActivity.objects.create(
            user=user,
            activity_type='registration',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            response.data['message'] = 'Account created successfully. Please check your email for verification.'
        return response

class UserLoginView(TokenObtainPairView):
    """
    User login endpoint with JWT token generation
    POST /api/auth/login/
    """
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        # Update last login and IP
        user.last_login = timezone.now()
        user.last_login_ip = self.get_client_ip()
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        # Log login activity
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class UserLogoutView(APIView):
    """
    User logout endpoint with token blacklisting
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Log logout activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='logout',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile management endpoint
    GET/PUT/PATCH /api/profile/
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def perform_update(self, serializer):
        user = serializer.save()
        # Log profile update activity
        UserActivity.objects.create(
            user=user,
            activity_type='profile_update',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        # Recalculate profile completeness
        user.profile.calculate_completeness()
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class PublicProfileView(generics.RetrieveAPIView):
    """
    Public user profile endpoint
    GET /api/profile/{username}/
    """
    serializer_class = PublicUserSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'username'
    
    def get_queryset(self):
        return CustomUser.objects.select_related('profile').all()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Increment profile views for public profiles
        if instance.is_profile_public:
            instance.profile.increment_profile_views()
            
            # Log profile view activity if user is authenticated
            if request.user.is_authenticated and request.user != instance:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='profile_view',
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class PasswordChangeView(APIView):
    """
    Password change endpoint
    POST /api/auth/password/change/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            
            # Log password change activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='password_change',
                ip_address=self.get_client_ip(),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class PasswordResetRequestView(APIView):
    """
    Password reset request endpoint
    POST /api/auth/password/reset/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = CustomUser.objects.get(email=email)
            
            # Create password reset token
            reset_token = PasswordResetToken.objects.create(
                user=user,
                ip_address=self.get_client_ip()
            )
            
            # Send reset email
            self.send_reset_email(user, reset_token.token)
            
            return Response({
                'message': 'Password reset instructions sent to your email'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_reset_email(self, user, token):
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/password-reset/{token}"
        subject = 'Password Reset Request'
        message = f"""
        Hi {user.username},
        
        You requested a password reset. Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        Your Progress Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class PasswordResetConfirmView(APIView):
    """
    Password reset confirmation endpoint
    POST /api/auth/password/reset/confirm/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                reset_token = PasswordResetToken.objects.get(token=token)
                
                if not reset_token.is_valid():
                    return Response({
                        'error': 'Token is expired or already used'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Reset password
                user = reset_token.user
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                
                # Log password reset activity
                UserActivity.objects.create(
                    user=user,
                    activity_type='password_reset',
                    ip_address=self.get_client_ip(),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                return Response({
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
                
            except PasswordResetToken.DoesNotExist:
                return Response({
                    'error': 'Invalid token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management (admin only)
    """
    queryset = CustomUser.objects.select_related('profile').all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_profile_public', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_login', 'username']
    ordering = ['-date_joined']
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        serializer = UserStatsSerializer(data={})
        serializer.is_valid()
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def public_profiles(self, request):
        """Get list of public profiles"""
        public_users = self.queryset.filter(is_profile_public=True)
        page = self.paginate_queryset(public_users)
        if page is not None:
            serializer = PublicUserSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PublicUserSerializer(public_users, many=True)
        return Response(serializer.data)

class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user activity tracking
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['activity_type']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Return activities for current user only"""
        return UserActivity.objects.filter(user=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user details
    GET /api/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_profiles_list(request):
    """
    Get list of public user profiles
    GET /api/profiles/public/
    """
    users = CustomUser.objects.filter(is_profile_public=True).select_related('profile')
    
    # Add search functionality
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(profile__job_title__icontains=search) |
            Q(profile__skills__icontains=search)
        )
    
    # Add filtering by experience level
    experience = request.GET.get('experience', '')
    if experience:
        users = users.filter(profile__experience_level=experience)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(users, 12)  # 12 profiles per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    serializer = PublicUserSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    """
    Upload user avatar
    POST /api/profile/avatar/
    """
    if 'avatar' not in request.FILES:
        return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    avatar_file = request.FILES['avatar']
    
    # Validate file size (max 5MB)
    if avatar_file.size > 5 * 1024 * 1024:
        return Response({'error': 'Avatar file too large. Max size is 5MB'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if avatar_file.content_type not in allowed_types:
        return Response({'error': 'Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Save avatar
    user = request.user
    user.avatar = avatar_file
    user.save()
    
    # Log avatar update activity
    UserActivity.objects.create(
        user=user,
        activity_type='avatar_update',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return Response({
        'message': 'Avatar uploaded successfully',
        'avatar_url': user.get_avatar_url()
    })

def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip