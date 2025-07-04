from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import ProgressProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create ProgressProfile when a new User is created"""
    if created:
        ProgressProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save ProgressProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()