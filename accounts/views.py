import secrets
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import login, logout, get_user_model
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from spotify_sync.tasks import sync_spotify_data
User = get_user_model()

def landing(request):
    return render(request, 'landing.html')

def spotify_login(request):
    state = secrets.token_urlsafe(16)
    #random string to avoid CSRF
    request.session['spotify_auth_state'] = state
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'scope': settings.SPOTIFY_SCOPES,
        'state': state,
    }
    auth_url = f"https://accounts.spotify.com/authorize/?{urlencode(params)}"
    return redirect(auth_url)

def spotify_callback(request): #spotify sends user here with code and state 
    state = request.GET.get('state') #verify that state matches (avoids CSRF attacks)
    expected_state = request.session.pop('spotify_auth_state', None)
    if state != expected_state:
        return redirect('/?error=state_mismatch')
    code = request.GET.get('code') #spotify gives us this code
    if not code:
        return redirect('/?error=no_code')
    token_resp = requests.post(
        'https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        },
        auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    token_data = token_resp.json()
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    expires_in = token_data['expires_in']
    # Step C: get the user's Spotify profile
    profile_resp = requests.get(
        'https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    profile = profile_resp.json()
    spotify_user_id = profile['id']
    display_name = profile.get('display_name', '')
    profile_picture_url = (
        profile['images'][0]['url'] if profile.get('images') else None
    )
    # Step D: find or create the Django User
    # We use spotify_user_id as the username — no password needed
    user, _ = User.objects.get_or_create(username=spotify_user_id)
    # Step E: find or create the SpotifyAccount linked to that user
    from accounts.models import SpotifyAccount
    spotify_account, _ = SpotifyAccount.objects.get_or_create(
        user=user,
        defaults={'spotify_user_id': spotify_user_id},
    )
    # Always update the token fields (they change every login)
    spotify_account.spotify_user_id = spotify_user_id
    spotify_account.display_name = display_name
    spotify_account.profile_picture_url = profile_picture_url
    spotify_account.access_token = access_token
    spotify_account.refresh_token = refresh_token
    spotify_account.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
    spotify_account.save()
    
    # Step F: Trigger the Spotify data sync in the background
    sync_spotify_data.delay(user.id)

    # Step G: log the user in and send them to the landing page
    login(request, user)
    return redirect('landing')   

def logout_view(request):
    logout(request)
    return redirect('landing')