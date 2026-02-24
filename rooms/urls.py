from django.urls import path
from . import views

app_name = 'rooms'
urlpatterns = [
    path('create/', views.create_room, name='create_room'),
    path('join/', views.join_room, name='join_room'),
    path('<str:room_code>/', views.lobby, name='lobby'),
]