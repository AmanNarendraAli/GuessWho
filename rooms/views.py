from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Room, RoomPlayer
from .utils import generate_room_code

@login_required(login_url='/')
def create_room(request):
    if request.method!='POST':
        return redirect('landing')
    for _ in range(10):
        code = generate_room_code()
        if not Room.objects.filter(code=code,status='lobby').exists(): #check if active room with same status exists
            break
        else:
            return render(request, 'landing.html', {
            'error': 'Could not generate a unique room code. Try again.'
        })
    
    room = Room.objects.create(code=code, host_user=request.user)
    display_name = getattr(
        getattr(request.user, 'spotify_account', None),
        'display_name', request.user.username
    ) #getattr - first arg is object, second is attribute name, third is default value if attribute not found
    RoomPlayer.objects.create(
        room=room,
        user=request.user,
        display_name=display_name,
        is_host=True
    )

    return redirect('rooms:lobby',room_code=room.code)

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
    
    if room.players.filter(user=request.user).exists(): #if user is already in the room
        return redirect('rooms:lobby', room_code=room.code)

    display_name = getattr(
        getattr(request.user, 'spotify_account', None), 
        'display_name', request.user.username
    )

    RoomPlayer.objects.create(
        room=room,
        user=request.user,
        display_name=display_name,
    ) #creating user object in the room

    return redirect('rooms:lobby', room_code=room.code)

@login_required(login_url='/')
def lobby(request, room_code):
    room = get_object_or_404(Room, code=room_code)

    # Make sure this user is actually in the room
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