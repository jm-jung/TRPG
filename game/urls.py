from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='game/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('start/', views.start_game, name='start_game'),
    path('play/<int:game_session_id>/', views.play_game, name='play_game'),
    path('result/<int:game_session_id>/', views.game_result, name='game_result'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)