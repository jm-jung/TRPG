from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt

from . import views
from django.contrib.auth import views as auth_views

from .views import csrf

app_name = 'game'  # URL 네임스페이스 추가
urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='game/login.html'), name='login'),

    path('logout/', views.logout_view, name='logout'),
    path('start/', views.start_game, name='start_game'),
    path('play/<int:game_session_id>/', views.play_game, name='play_game'),
    path('result/<int:game_session_id>/', views.game_result, name='game_result'),

    # 새로운 API 엔드포인트 추가
    path('api/start-game/', views.start_game, name='api_start_game'),
    path('api/process-dialogue/<int:game_session_id>/', views.process_dialogue, name='process_dialogue'),
    path('api/game-state/<int:game_session_id>/', views.api_get_game_state, name='api_get_game_state'),

    path('api/get-csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    path('api/set-csrf-token/', views.set_csrf_token, name='set_csrf_token'),
    path('csrf/', csrf),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)