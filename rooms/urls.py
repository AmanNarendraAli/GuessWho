from django.urls import path
from . import views

app_name = 'rooms'
urlpatterns = [
    path('create/', views.create_room, name='create_room'),
    path('join/', views.join_room, name='join_room'),
    path('<str:room_code>/', views.lobby, name='lobby'),
    path('<str:room_code>/leave/', views.leave_room, name='leave_room'),
    path('<str:room_code>/beacon-leave/', views.beacon_leave_room, name='beacon_leave_room'),
]