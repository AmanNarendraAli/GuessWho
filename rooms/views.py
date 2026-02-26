from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Room, RoomPlayer
from .utils import generate_room_code


# ── Helpers ──────────────────────────────────────────────────

def get_active_room_membership(user):
    """Return the user's RoomPlayer in any active (non-closed/finished) room, or None."""
    return RoomPlayer.objects.filter(
        user=user,
        room__status__in=['lobby', 'starting', 'in_game'],
    ).select_related('room').first()


def _leave_room_cleanup(room_player):
    """Remove a player from their room, transferring host if needed."""
    room = room_player.room
    was_host = room_player.is_host
    room_player.delete()

    if was_host:
        next_player = room.players.order_by('joined_at').first()
        if next_player:
            next_player.is_host = True
            next_player.save(update_fields=['is_host'])
        else:
            room.status = 'closed'
            room.save(update_fields=['status'])


# ── Views ────────────────────────────────────────────────────

@login_required(login_url='/')
def create_room(request):
    if request.method != 'POST':
        return redirect('landing')

    # Check if user is already in a room
    existing = get_active_room_membership(request.user)
    if existing:
        # If client hasn't confirmed yet, ask for confirmation
        if request.POST.get('confirm') != '1':
            return JsonResponse({
                'confirm_needed': True,
                'current_room': existing.room.code,
                'action': 'create',
            })
        # User confirmed — leave old room first
        _leave_room_cleanup(existing)

    for _ in range(10):
        code = generate_room_code()
        if not Room.objects.filter(code=code, status='lobby').exists():
            break
    else:
        return render(request, 'landing.html', {
            'error': 'Could not generate a unique room code. Try again.'
        })

    room = Room.objects.create(code=code, host_user=request.user)
    display_name = getattr(
        getattr(request.user, 'spotify_account', None),
        'display_name', request.user.username
    )
    RoomPlayer.objects.create(
        room=room,
        user=request.user,
        display_name=display_name,
        is_host=True,
    )

    return redirect('rooms:lobby', room_code=room.code)


@login_required(login_url='/')
def join_room(request):
    if request.method != 'POST':
        return redirect('landing')

    code = request.POST.get('room_code', '').strip().upper()
    if not code:
        return render(request, 'landing.html', {
            'error': 'Please enter a room code.'
        })

    room = Room.objects.filter(code=code, status='lobby').first()

    if not room:
        return render(request, 'landing.html', {
            'error': f'Room "{code}" not found or already started.'
        })

    current_count = room.players.count()
    if current_count >= room.max_players:
        return render(request, 'landing.html', {
            'error': 'That room is full.'
        })

    if room.players.filter(user=request.user).exists():
        return redirect('rooms:lobby', room_code=room.code)

    # Check if user is already in a different room
    existing = get_active_room_membership(request.user)
    if existing:
        if request.POST.get('confirm') != '1':
            return JsonResponse({
                'confirm_needed': True,
                'current_room': existing.room.code,
                'target_room': code,
                'action': 'join',
            })
        _leave_room_cleanup(existing)

    display_name = getattr(
        getattr(request.user, 'spotify_account', None),
        'display_name', request.user.username
    )

    RoomPlayer.objects.create(
        room=room,
        user=request.user,
        display_name=display_name,
    )

    return redirect('rooms:lobby', room_code=room.code)


@login_required(login_url='/')
def lobby(request, room_code):
    room = get_object_or_404(Room, code=room_code)

    room_player = room.players.filter(user=request.user).first()
    if not room_player:
        return redirect('landing')

    players = room.players.select_related('user__spotify_account').all()
    is_host = room_player.is_host

    return render(request, 'lobby.html', {
        'room': room,
        'players': players,
        'is_host': is_host,
    })


@login_required(login_url='/')
def leave_room(request, room_code):
    room = get_object_or_404(Room, code=room_code)
    room_player = room.players.filter(user=request.user).first()

    if room_player:
        _leave_room_cleanup(room_player)

    return redirect('landing')


@csrf_exempt
def beacon_leave_room(request, room_code):
    """Called by navigator.sendBeacon() on tab close. CSRF-exempt because beacons can't carry tokens."""
    if request.method != 'POST' or not request.user.is_authenticated:
        return HttpResponse(status=204)

    room = Room.objects.filter(code=room_code).first()
    if not room:
        return HttpResponse(status=204)

    room_player = room.players.filter(user=request.user).first()
    if room_player:
        _leave_room_cleanup(room_player)

    return HttpResponse(status=204)