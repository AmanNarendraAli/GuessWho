from django.db import models
from django.conf import settings

class SpotifyTrack(models.Model):
    spotify_track_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=500)
    artist_name = models.CharField(max_length=500)
    album_image_url = models.URLField(max_length=1000, blank=True, null=True)
    preview_url = models.URLField(max_length=1000, blank=True, null=True)
    external_url = models.URLField(max_length=1000, blank=True, null=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.artist_name}"

class UserTrackEvidence(models.Model):
    SOURCE_CHOICES = [
        ('top_short', 'Top Tracks - Short Term'),
        ('top_medium', 'Top Tracks - Medium Term'),
        ('top_long', 'Top Tracks - Long Term'),
        ('recent', 'Recently Played'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    track = models.ForeignKey(SpotifyTrack, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_rank = models.IntegerField(null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'track', 'source_type']
        indexes = [
            models.Index(fields=['track']),
            models.Index(fields=['user']),
            models.Index(fields=['user', 'source_type']),
        ]

    def __str__(self):
        return f"{self.user} → {self.track} ({self.source_type})"