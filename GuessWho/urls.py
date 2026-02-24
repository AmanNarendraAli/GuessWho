from django.contrib import admin
from django.urls import path, include
from accounts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('auth/', include('accounts.urls', namespace='accounts')),
    path('rooms/', include('rooms.urls', namespace='rooms')),
]
