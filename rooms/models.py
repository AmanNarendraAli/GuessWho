from django.db import models
from django.conf import settings

class Room(models.Model):
    STATUS_CHOICES = [
        ('lobby', 'Lobby'),
        ('starting', 'Starting'),
        ('in_game', 'In Game'),
        ('finished', 'Finished'),
        ('closed', 'Closed'),
    ]

    code = models.CharField(max_length=5,unique=True,blank=True)
    host_user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='hosted_rooms')
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='lobby')
    created_at = models.DateTimeField(auto_now_add=True)
    min_players = models.IntegerField(default=2)
    max_players = models.IntegerField(default=8)
    class Meta:
        indexes = [models.Index(fields=['status']),] #this index is used to speed up queries that filter by status
    def __str__(self):
        return f"Room {self.code} ({self.status})"

class RoomPlayer(models.Model):
    CONNECTION_CHOICES = [
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
    ]

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='players'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_memberships'
    )
    display_name = models.CharField(max_length=255)
    is_host = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    connection_state = models.CharField(
        max_length=20, choices=CONNECTION_CHOICES, default='connected'
    )

    class Meta:
        unique_together = ['room', 'user']
        indexes = [
            models.Index(fields=['room', 'connection_state']),
        ]

    def __str__(self):
        host_tag = " (HOST)" if self.is_host else ""
        return f"{self.display_name} in {self.room.code}{host_tag}"
