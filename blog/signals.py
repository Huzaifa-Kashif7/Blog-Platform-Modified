from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Ensure every user has a profile."""
    if created:
        UserProfile.objects.create(user=instance, short_name=instance.get_full_name() or instance.username)
    else:
        # Update short name if empty
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        if not profile.short_name:
            profile.short_name = instance.get_full_name() or instance.username
            profile.save(update_fields=['short_name'])

