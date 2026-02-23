from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
import requests
User = get_user_model()

@shared_task
def sync_spotify_data(user_id):
    from accounts.models import SpotifyAccount
    from accounts.utils import refresh_spotify_token
    from spotify_sync.models import SpotifyTrack, UserTrackEvidence
    user = User.objects.get(pk=user_id)
    spotify_account = SpotifyAccount.objects.get(user=user)
    # Mark as syncing
    spotify_account.sync_status = 'syncing'
    spotify_account.save(update_fields=['sync_status'])
    try:
        # Refresh token if needed
        access_token = refresh_spotify_token(spotify_account)
        headers = {'Authorization': f'Bearer {access_token}'}
        # ── Fetch top tracks for all 3 time ranges ──────────────────
        time_ranges = [
            ('top_short',  'short_term'),
            ('top_medium', 'medium_term'),
            ('top_long',   'long_term'),
        ]
        for source_type, time_range in time_ranges:
            resp = requests.get(
                'https://api.spotify.com/v1/me/top/tracks',
                headers=headers,
                params={'time_range': time_range, 'limit': 50},
            )
            resp.raise_for_status()
            items = resp.json().get('items', [])
            for rank, item in enumerate(items, start=1):
                _upsert_track_and_evidence(user, item, source_type, source_rank=rank)
        # ── Fetch recently played ────────────────────────────────────
        resp = requests.get(
            'https://api.spotify.com/v1/me/player/recently-played',
            headers=headers,
            params={'limit': 50},
        )
        resp.raise_for_status()
        play_history = resp.json().get('items', [])
        for entry in play_history:
            item = entry['track']
            played_at = entry['played_at']  # ISO 8601 string
            _upsert_track_and_evidence(user, item, 'recent', seen_at=played_at)
        # ── Mark synced ──────────────────────────────────────────────
        spotify_account.sync_status = 'synced'
        spotify_account.last_synced_at = timezone.now()
        spotify_account.save(update_fields=['sync_status', 'last_synced_at'])
    except Exception as exc:
        spotify_account.sync_status = 'failed'
        spotify_account.save(update_fields=['sync_status'])
        raise exc   # re-raise so Celery marks the task as FAILURE
def _upsert_track_and_evidence(user, track_item, source_type, source_rank=None, seen_at=None):
    """Helper: upsert SpotifyTrack, then upsert UserTrackEvidence."""
    from spotify_sync.models import SpotifyTrack, UserTrackEvidence
    from django.utils.dateparse import parse_datetime
    artists = track_item.get('artists', [])
    artist_name = ', '.join(a['name'] for a in artists) if artists else ''
    images = track_item.get('album', {}).get('images', [])
    album_image_url = images[0]['url'] if images else None
    external_urls = track_item.get('external_urls', {})
    track, _ = SpotifyTrack.objects.update_or_create(
        spotify_track_id=track_item['id'],
        defaults={
            'name': track_item['name'],
            'artist_name': artist_name,
            'album_image_url': album_image_url,
            'preview_url': track_item.get('preview_url'),
            'external_url': external_urls.get('spotify'),
            'duration_ms': track_item.get('duration_ms'),
        },
    )
    seen_at_parsed = parse_datetime(seen_at) if seen_at else None
    UserTrackEvidence.objects.update_or_create(
        user=user,
        track=track,
        source_type=source_type,
        defaults={
            'source_rank': source_rank,
            'seen_at': seen_at_parsed,
        },
    )