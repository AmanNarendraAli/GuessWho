from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('spotify/logout/', views.logout_view, name='spotify_logout'),
]