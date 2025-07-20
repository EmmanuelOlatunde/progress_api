from django.test import TestCase
from django.contrib.auth import get_user_model
from users.models import UserProfile
from django.db.models.signals import post_save
from users.signals import create_user_profile, save_user_profile

CustomUser = get_user_model()

class UserProfileSignalTests(TestCase):
    def setUp(self):
        # Disconnect signals to prevent interference during setup
        post_save.disconnect(create_user_profile, sender=CustomUser)
        post_save.disconnect(save_user_profile, sender=CustomUser)
        
    def tearDown(self):
        # Reconnect signals after tests
        post_save.connect(create_user_profile, sender=CustomUser)
        post_save.connect(save_user_profile, sender=CustomUser)

    def test_create_user_profile_signal(self):
        """Test that UserProfile is created when a new user is created"""
        # Reconnect create_user_profile signal for this test
        post_save.connect(create_user_profile, sender=CustomUser)
        
        # Create a new user
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Check if UserProfile was created
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)
        
        # Disconnect signal again
        post_save.disconnect(create_user_profile, sender=CustomUser)

    def test_create_user_profile_signal_not_triggered_on_update(self):
        """Test that creating a profile doesn't trigger on user update"""
        # Create user and profile manually
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=user)
        
        # Store initial profile count
        initial_count = UserProfile.objects.count()
        
        # Update user
        user.email = 'newemail@example.com'
        user.save()
        
        # Check that no new profile was created
        self.assertEqual(UserProfile.objects.count(), initial_count)

    def test_save_user_profile_signal_with_existing_profile(self):
        """Test that save_user_profile signal updates existing profile"""
        # Reconnect save_user_profile signal
        post_save.connect(save_user_profile, sender=CustomUser)
        
        # Create user and profile
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        profile = UserProfile.objects.get_or_create(user=user)
        
        # Modify user and save
        user.username = 'newusername'
        user.save()
        
        # Refresh profile from database and verify it still exists and is linked
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)

    def test_save_user_profile_signal_without_profile(self):
        """Test that save_user_profile creates profile if none exists"""
        # Reconnect save_user_profile signal
        post_save.connect(save_user_profile, sender=CustomUser)
        
        # Create user without profile
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Check that profile was created
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)
        
        # Disconnect signal
        post_save.disconnect(save_user_profile, sender=CustomUser)

    def test_signal_receiver_uniqueness(self):
        """Test that signals don't create duplicate profiles"""
        # Reconnect both signals
        post_save.connect(create_user_profile, sender=CustomUser)
        post_save.connect(save_user_profile, sender=CustomUser)
        
        # Create user
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Check only one profile exists
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)