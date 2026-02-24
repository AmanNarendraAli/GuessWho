import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Room, RoomPlayer

class RoomConsumer(WebsocketConsumer):
    # handles websocket connections for a room
    def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code'] #extracts room code from URL 
        self.room_group_name = f'room_{self.room_code}'
        self.user = self.scope['user'] #extracts user from scope. scope = request in http
        if self.user.is_anonymous:
            self.close()
            return
        try:
            self.room = Room.objects.get(code=self.room_code)
            self.room_player = RoomPlayer.objects.get(room = self.room, user = self.user)
        except (Room.DoesNotExist, RoomPlayer.DoesNotExist):
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(self.room_group_name,self.channel_name) #adds this weksocket to a group named 'room_code'
        self.accept()
        self.room_player.connection_state = 'connected'
        self.room_player.save(update_fields=['connection_state'])
        self._broadcast_room_state()

    def disconnect(self,close_code):
        if hasattr(self,'room_player'):
            self.room_player.connection_state = 'disconnected'
            self.room_player.save(update_fields=['connection_state'])
        if hasattr(self, 'room_group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name, self.channel_name
            )
        self._broadcast_room_state()

    def receive(self, text_data):
        """Handle incoming messages from clients."""
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'match.start':
            self._handle_start_game()
    
    def _handle_start_game(self):
        # Only the host can start
        if not self.room_player.is_host:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Only the host can start the game.'
            }))
            return

        # Refresh room state
        self.room.refresh_from_db()
        if self.room.status != 'lobby':
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Game has already started.'
            }))
            return

        players = self.room.players.select_related(
            'user__spotify_account'
        ).all()
        player_count = players.count()

        # Check player count
        if player_count < self.room.min_players:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Need at least {self.room.min_players} players.'
            }))
            return

        # Check all synced
        all_synced = all(
            getattr(p.user, 'spotify_account', None)
            and p.user.spotify_account.sync_status == 'synced'
            for p in players
        )
        if not all_synced:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'All players must be synced before starting.'
            }))
            return

        # All checks passed — transition room
        self.room.status = 'starting'
        self.room.save(update_fields=['status'])

        # Broadcast to everyone
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'match.starting',
                'message': 'Game is starting!',
            }
        )
    
    def _broadcast_room_state(self):
        # broadcast room state to all clients in room
        self.room.refresh_from_db()
        players = self.room.players.select_related(
            'user__spotify_account'
        ).order_by('joined_at') #orders players by when they joined

        player_data = []
        all_synced = True
        for p in players:
            spotify = getattr(p.user, 'spotify_account', None)
            sync_status = spotify.sync_status if spotify else 'not_synced'
            if sync_status != 'synced':
                all_synced = False #if any player is not synced, set all_synced to False
            player_data.append({
                'user_id': p.user.id,
                'display_name': p.display_name,
                'is_host': p.is_host,
                'sync_status': sync_status,
                'connection_state': p.connection_state,
            })

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'room.state',
                'players': player_data,
                'all_synced': all_synced,
                'player_count': len(player_data),
                'room_status': self.room.status,
            } #sends message to all clients in room that the room state has changed
        )

        #group message handlers - called when a group_send message is received
        def room_state(self, event):
            self.send(text_data=json.dumps({
                'type':'room.state',
                'players':event['players'],
                'all_synced':event['all_synced'],
                'player_count':event['player_count'],
                'room_status':event['room_status'],
            }))

        def match_starting(self,event):
            self.send(text_data=json.dumps({
                'type':'match.starting',
                'message':event['message'],
            }))