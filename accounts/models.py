from django.db import models
from django.conf import settings 
# Create your models here.

class SpotifyAccount(models.Model):
    SYNC_STATUS_CHOICES = [
        ('not_synced', 'Not Synced'),
        ('syncing', 'Syncing'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="spotify_account")
    spotify_user_id = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    profile_picture_url = models.URLField(max_length=1000, blank=True, null=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=20, choices=SYNC_STATUS_CHOICES, default='not_synced'
    )
    scopes_granted = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.display_name} ({self.spotify_user_id})"