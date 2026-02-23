import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

def refresh_spotify_token(spotify_account):
    #refreshes account token
    if (spotify_account.token_expires_at and 
        spotify_account.token_expires_at > timezone.now() + timedelta(seconds=60)):
        return spotify_account.access_token

    # Expired — get a new one
    resp = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'refresh_token',
            'refresh_token': spotify_account.refresh_token,
        },
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    resp.raise_for_status()
    data = resp.json()

    spotify_account.access_token = data['access_token']
    spotify_account.token_expires_at = timezone.now() + timedelta(seconds=data['expires_in'])
    # Spotify sometimes issues a new refresh token; take it if offered
    if 'refresh_token' in data:
        spotify_account.refresh_token = data['refresh_token']
    spotify_account.save()

    return spotify_account.access_token
