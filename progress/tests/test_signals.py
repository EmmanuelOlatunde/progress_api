from django.test import TestCase
from django.contrib.auth import get_user_model
from progress.models import ProgressProfile

User = get_user_model()

class UserSignalTests(TestCase):
    def test_create_user_profile_signal_creates_profile(self):
        """Creating a user should trigger a ProgressProfile creation"""
        user = User.objects.create_user(username="testuser", password="testpass")
        
        # Check profile exists
        self.assertTrue(
            ProgressProfile.objects.filter(user=user).exists(),
            "ProgressProfile should be created automatically"
        )
        
        profile = ProgressProfile.objects.get(user=user)
        self.assertEqual(profile.user, user)
    
    def test_create_user_profile_signal_does_not_duplicate(self):
        """Saving the same user again should NOT create duplicate profiles"""
        user = User.objects.create_user(username="testuser2", password="testpass")
        # Saving again should NOT trigger another profile creation
        user.save()
        
        profiles = ProgressProfile.objects.filter(user=user)
        self.assertEqual(profiles.count(), 1, "Should not create duplicate profiles on save")

    def test_save_user_profile_signal_saves_existing_profile(self):
        """Saving a user should also save their associated profile"""
        user = User.objects.create_user(username="testuser3", password="testpass")
        profile = ProgressProfile.objects.get(user=user)

        # Simulate modifying profile directly
        profile.total_xp = 50
        profile.save()

        # Now saving user should trigger profile.save()
        # (We'll spy by modifying a field & checking no errors occur)
        user.first_name = "Updated"
        user.save()  # Should trigger save_user_profile signal

        # Reload profile to ensure it still exists and was saved
        updated_profile = ProgressProfile.objects.get(user=user)
        self.assertEqual(updated_profile.total_xp, 50, "Profile save signal should not overwrite changes")

    def test_save_user_profile_signal_handles_missing_profile_gracefully(self):
        """If a user somehow has no profile, signal should not crash"""
        user = User.objects.create_user(username="testuser4", password="testpass")
        
        # Manually delete profile
        ProgressProfile.objects.filter(user=user).delete()
        
        # Saving user should NOT raise an error
        try:
            user.save()
        except Exception as e:
            self.fail(f"Signal raised an unexpected exception: {e}")
