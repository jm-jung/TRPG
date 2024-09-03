from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from .chatbot import generate_demon_lord_response, analyze_player_message
from .models import  Player, GameSession, Dialogue, GameState,StoryProgress
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
import json
import openai
from django.conf import settings

def home(request):
    return render(request, 'game/home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'game/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')


def start_game(request):
    player, created = Player.objects.get_or_create(user=request.user)
    game_session = GameSession.objects.create(player=player)
    StoryProgress.objects.create(game_session=game_session)
    GameState.objects.create(game_session=game_session)
    return redirect('play_game', game_session_id=game_session.id)


@login_required
def play_game(request, game_session_id):
    game_session = GameSession.objects.get(id=game_session_id)
    if request.method == 'POST':
        return process_dialogue(request, game_session)
    context = {
        'game_session': game_session,
        'dialogues': game_session.dialogues.order_by('timestamp'),
        'story_progress': game_session.storyprogress,
        'game_state': game_session.gamestate,
    }
    return render(request, 'game/play.html', context)


def process_dialogue(request, game_session):
    player_message = request.POST.get('message')

    # 플레이어 대화 저장
    Dialogue.objects.create(
        game_session=game_session,
        speaker='영웅',
        content=player_message
    )

    # AI를 사용하여 마왕의 응답 생성
    demon_lord_response = generate_demon_lord_response(player_message)

    # 마왕 대화 저장
    Dialogue.objects.create(
        game_session=game_session,
        speaker='마왕',
        content=demon_lord_response
    )

    # 게임 상태 업데이트
    update_game_state(game_session, player_message, demon_lord_response)

    # 스토리 진행 업데이트
    update_story_progress(game_session)

    # 게임 종료 조건 확인
    if check_game_end(game_session):
        end_game(game_session)

    return JsonResponse({
        'demon_lord_response': demon_lord_response,
        'game_state': game_session.gamestate.__dict__,
        'story_progress': game_session.storyprogress.__dict__,
    })


def update_game_state(game_session, player_message, story_progress, calculate_resistance_decrease=None):
    game_state = game_session.gamestate

    # 플레이어 메시지 분석
    player_analysis = analyze_player_message(player_message)

    # 악마 군주의 응답 생성
    demon_lord_response = generate_demon_lord_response(player_message, game_state, story_progress)

    # 플레이어의 설득력 업데이트
    persuasion_increase = player_analysis['persuasion_strength']
    game_state.player_persuasion_level = min(100, game_state.player_persuasion_level + persuasion_increase)

    # 악마 군주의 저항력 업데이트
    resistance_decrease = calculate_resistance_decrease(player_analysis, game_state)
    game_state.demon_lord_resistance = max(0, game_state.demon_lord_resistance - resistance_decrease)

    # 감정 상태 업데이트
    game_state.player_emotional_state = update_emotional_state(game_state.player_emotional_state, player_analysis['emotional_impact'])
    game_state.demon_lord_emotional_state = update_demon_lord_emotion(game_state, resistance_decrease)

    # 주장 강도 계산
    game_state.argument_strength = calculate_argument_strength(
        game_state.player_persuasion_level,
        game_state.demon_lord_resistance,
        player_analysis['primary_approach']
    )

    # 환경 요인 업데이트 (예시)
    update_environmental_factors(game_state.environmental_factors, player_message)

    # 게임 종료 조건 확인
    if game_state.player_persuasion_level >= 100 or game_state.demon_lord_resistance <= 0:
        game_session.is_completed = True
        game_session.save()

    game_state.save()
    return game_state, demon_lord_response

def update_story_progress(game_session):
    story_progress = game_session.storyprogress
    # 여기에 스토리 진행 업데이트 로직을 구현합니다.
    story_progress.save()


def check_game_end(game_session):
    # 게임 종료 조건을 확인하는 로직을 구현합니다.
    return False


def end_game(game_session):
    game_session.is_active = False
    game_session.end_time = timezone.now()
    game_session.save()

@login_required
def game_result(request, game_session_id):
    game_session = GameSession.objects.get(id=game_session_id)
    context = {
        'game_session': game_session,
        'dialogues': game_session.dialogues.order_by('timestamp'),
        'final_state': game_session.gamestate,
    }
    return render(request, 'game/result.html', context)