import logging
from typing import Optional, Callable, Tuple, Dict

from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponseBadRequest
from .chatbot import generate_demon_lord_response, analyze_player_message
from .models import Player, GameSession, Dialogue, GameState, StoryProgress, GameResult
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from .game_logic import update_emotional_state, update_demon_lord_emotion, calculate_argument_strength, \
    update_environmental_factors, update_game_state, update_story_progress
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
            return redirect('game:login')
    else:
        form = UserCreationForm()
    return render(request, 'game/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('game:home')


logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def start_game(request):
    try:
        player, created = Player.objects.get_or_create(user=request.user)

        game_session = GameSession.objects.create(
            player=player,  # ForeignKey로 연결된 player 필드
            is_active=True,  # 기본값은 True이므로 명시적으로 지정할 필요 없음
            is_completed=False,
            start_time=timezone.now(),  # 시작 시간을 현재 시간으로 설정
            outcome='ongoing',  # 기본값이 있으므로 생략 가능
            result='ongoing'  # 기본값이 있으므로 생략 가능
        )

        StoryProgress.objects.create(
            game_session=game_session,
            current_chapter=1,
            progress=0
        )

        logger.info(f"Game started successfully for user {request.user.username}")
        return JsonResponse({
            "status": "success",
            "message": "게임이 시작되었습니다.",
            "game_session_id": game_session.id
        })
    except Exception as e:
        logger.error(f"Error starting game for user {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": "게임 시작 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        }, status=500)


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def play_game(request, game_session_id):
    try:
        game_session = GameSession.objects.select_related('player').get(
            id=game_session_id,
            player__user=request.user,
            is_active=True
        )

        # GameState가 없으면 생성
        game_state, created = GameState.objects.get_or_create(game_session=game_session)

        # StoryProgress가 없으면 생성
        story_progress, created = StoryProgress.objects.get_or_create(
            game_session=game_session,
            defaults={'current_chapter': 1, 'chapter_progress': 0}
        )

    except GameSession.DoesNotExist:
        logger.warning(f"Active game session not found for user {request.user.username}")
        return JsonResponse({"error": "Active game session not found"}, status=404)

    if request.method == "POST":
        message = request.POST.get('message')
        if not message:
            return JsonResponse({"error": "No message provided"}, status=400)

        try:
            with transaction.atomic():
                # 플레이어 메시지 분석
                analysis_result = analyze_player_message(message)

                # 게임 상태 업데이트
                game_session = update_game_state(game_session, analysis_result)

                # 마왕의 응답 생성
                story_progress = game_session.storyprogress_set.first()  # StoryProgress 모델과의 관계 가정
                demon_lord_response = generate_demon_lord_response(
                    message,
                    game_session,
                    story_progress
                )

                # 게임 세션 저장
                game_session.save()

                logger.info(f"Game turn processed for user {request.user.username}")

                return JsonResponse({
                    'demon_lord_response': demon_lord_response,
                    'game_state': {
                        'player_persuasion_level': game_session.player.persuasion_level,
                        'player_emotional_state': game_session.player_emotional_state,
                        'demon_lord_resistance': game_session.demon_lord_resistance,
                        'demon_lord_emotional_state': game_session.demon_lord_emotional_state,
                        'argument_strength': game_session.argument_strength,
                        'current_chapter': story_progress.current_chapter,
                        'chapter_progress': story_progress.chapter_progress,
                    }
                })
        except Exception as e:
            logger.exception(f"Error processing game turn: {str(e)}")
            return JsonResponse({"error": "An unexpected error occurred during the game turn."}, status=500)
    else:
        # GET 요청 처리
        context = {
            'game_session': game_session,
            'game_state': game_session.gamestate,
            'story_progress': game_session.storyprogress,
            'player': game_session.player,
        }
        return render(request, 'game/play.html', context)


import re
from collections import Counter


def analyze_dialogue_content(message):
    # 키워드 목록 (예시)
    keywords = {
        '평화': 5,
        '협력': 5,
        '이해': 4,
        '대화': 4,
        '설득': 3,
        '동의': 3,
        '타협': 3,
        '위협': -2,
        '공격': -3,
        '파괴': -4,
        '마왕': 2,
        '영웅': 2,
        '세계': 1,
        '운명': 1,
        '뿡': 50
    }

    # 감정 표현 패턴 (예시)
    emotion_patterns = {
        r'\b기쁘|즐겁|행복': ('positive', 3),
        r'\b슬프|우울|속상': ('negative', -2),
        r'\b화나|짜증|분노': ('angry', -3),
        r'\b두렵|무서': ('fear', -2),
        r'\b감사|고마': ('gratitude', 4),
        r'\b놀라|깜짝': ('surprise', 1),
        r'\b기대|희망': ('hopeful', 2)
    }

    score = 0
    used_keywords = Counter()
    emotions = Counter()
    total_emotion_score = 0

    # 키워드 분석
    for word, value in keywords.items():
        print(word, value, end=" ")
        count = message.count(word)
        print(count)
        score += count * value
        if count > 0:
            used_keywords[word] = count

    # 감정 표현 분석
    for pattern, (emotion, value) in emotion_patterns.items():
        matches = re.findall(pattern, message)
        if matches:
            emotions[emotion] += len(matches)
            total_emotion_score += value * len(matches)

    # 주요 주제 식별
    main_topics = [word for word, count in used_keywords.most_common(3)]

    # 문장 복잡성 (간단한 측정)
    sentence_count = len(re.findall(r'\w+[.!?]', message))
    complexity = len(message.split()) / max(sentence_count, 1)

    return {
        'score': score,
        'used_keywords': dict(used_keywords),
        'emotions': dict(emotions),
        'emotion_score': total_emotion_score,
        'main_topics': main_topics,
        'length': len(message),
        'complexity': complexity,
        'dominant_emotion': emotions.most_common(1)[0][0] if emotions else None
    }


@require_POST
@csrf_protect
@transaction.atomic
def process_dialogue(request, game_session_id):
    try:
        game_session = GameSession.objects.select_related('player', 'gamestate', 'storyprogress').get(
            id=game_session_id)
    except GameSession.DoesNotExist:
        logger.warning(f"게임 세션을 찾을 수 없습니다: {game_session_id}")
        return JsonResponse({"error": "게임 세션을 찾을 수 없습니다"}, status=404)

    player_message = request.POST.get('message')

    if not player_message:
        return HttpResponseBadRequest("메시지 내용이 비어있습니다.")

    try:
        # 대화 내용 분석
        dialogue_analysis = analyze_dialogue_content(player_message)
        Dialogue.objects.create(
            game_session=game_session,
            speaker='영웅',
            content=player_message
        )
        # AI를 사용하여 마왕의 응답 생성
        demon_lord_response, demon_lord_analysis = generate_demon_lord_response(
            player_message,
            game_session.gamestate,
            game_session.storyprogress.current_chapter
        )
        Dialogue.objects.create(
            game_session=game_session,
            speaker='마왕',
            content=demon_lord_response
        )
        # 게임 상태 업데이트
        updated_game_state = update_game_state(
            game_session,
            player_message,
            demon_lord_response,
            dialogue_analysis
        )

        # 응답 데이터 준비
        response_data = {
            'demon_lord_response': demon_lord_response,
            'game_state': updated_game_state,
            'dialogue_analysis': dialogue_analysis,
            'demon_lord_analysis': demon_lord_analysis,
        }

        is_game_ended, end_result = check_game_end(game_session)
        if is_game_ended:
            response_data['game_end'] = {
                'result': end_result['result'],
                'message': end_result['description']
            }
        logger.info(f"대화가 처리되었습니다. 게임 세션: {game_session_id}")
        return JsonResponse(response_data)

    except Exception as e:
        logger.exception(f"대화 처리 중 오류 발생. 게임 세션 {game_session_id}: {str(e)}")
        return JsonResponse({'error': "대화 처리 중 예기치 못한 오류가 발생했습니다."}, status=500)


# def process_dialogue(request, game_session_id):
#     try:
#         game_session = GameSession.objects.select_related('player', 'gamestate', 'storyprogress').get(
#             id=game_session_id)
#     except GameSession.DoesNotExist:
#         logger.warning(f"게임 세션을 찾을 수 없습니다: {game_session_id}")
#         return JsonResponse({"error": "게임 세션을 찾을 수 없습니다"}, status=404)
#
#     player_message = request.POST.get('message')
#
#     if not player_message:
#         return HttpResponseBadRequest("메시지 내용이 비어있습니다.")
#
#     try:
#         # 대화 내용 분석
#         dialogue_analysis = analyze_dialogue_content(player_message)
#
#         # 플레이어 대화 저장
#         Dialogue.objects.create(
#             game_session=game_session,
#             speaker='영웅',
#             content=player_message
#         )
#
#         # AI를 사용하여 마왕의 응답 생성
#         demon_lord_response = generate_demon_lord_response(player_message, game_session.gamestate,
#                                                            game_session.storyprogress)
#
#         # 마왕 대화 저장
#         Dialogue.objects.create(
#             game_session=game_session,
#             speaker='마왕',
#             content=demon_lord_response
#         )
#
#         # 게임 상태 및 스토리 진행 업데이트 (대화 분석 결과 포함)
#         update_game_state(game_session, player_message, demon_lord_response, dialogue_analysis)
#         update_story_progress(game_session, dialogue_analysis)
#
#         # 게임 종료 조건 확인
#         game_end_result = check_game_end(game_session)
#         is_game_ended = bool(game_end_result)
#         if is_game_ended:
#             end_game(game_session, game_end_result)
#
#         # 응답 데이터 준비
#         response_data = {
#             'demon_lord_response': demon_lord_response,
#             'game_state': {
#                 'player_persuasion_level': game_session.player.persuasion_level,
#                 'player_emotional_state': game_session.player_emotional_state,
#                 'demon_lord_resistance': game_session.demon_lord_resistance,
#                 'demon_lord_emotional_state': game_session.demon_lord_emotional_state,
#                 'argument_strength': game_session.argument_strength,
#             },
#             'story_progress': {
#                 'current_chapter': game_session.storyprogress.current_chapter,
#                 'chapter_progress': game_session.storyprogress.chapter_progress,
#             },
#             'dialogue_analysis': dialogue_analysis,
#             'is_game_ended': is_game_ended,
#             'game_result': game_end_result if is_game_ended else None
#         }
#
#         logger.info(f"대화가 처리되었습니다. 게임 세션: {game_session_id}")
#         return JsonResponse(response_data)
#
#     except Exception as e:
#         logger.exception(f"대화 처리 중 오류 발생. 게임 세션 {game_session_id}: {str(e)}")
#         return JsonResponse({'error': "대화 처리 중 예기치 못한 오류가 발생했습니다."}, status=500)


# update_game_state와 update_story_progress 함수도 dialogue_analysis 매개변수를 받도록 수정해야 합니다.
# @transaction.atomic
# def update_story_progress(story_progress, game_state, player_message, dialogue_analysis):
#     MAX_TURNS = 10
#     current_turn = story_progress.current_chapter
#
#     # 플레이어의 설득력에 따른 진행도 증가
#     progress_increase = game_state.player_persuasion_level
#     story_progress.progress += progress_increase
#
#     # 진행도가 100 이상이면 다음 챕터로 넘어감
#     if story_progress.progress >= 100:
#         story_progress.current_chapter += 1
#         story_progress.progress = 0
#
#     # 플롯 포인트 추가 및 관리
#     new_plot_point = None
#     if "평화" in dialogue_analysis['used_keywords'] or "협력" in dialogue_analysis['used_keywords']:
#         new_plot_point = {
#             "type": "peace_proposal",
#             "chapter": story_progress.current_chapter,
#             "description": "플레이어가 평화적 해결책 제안",
#             "impact": {
#                 "player_persuasion": game_state.player_persuasion_level,
#                 "demon_resistance": game_state.demon_lord_resistance
#             }
#         }
#     elif dialogue_analysis['score'] > 50:  # 높은 대화 점수
#         new_plot_point = {
#             "type": "successful_argument",
#             "chapter": story_progress.current_chapter,
#             "description": "플레이어가 강력한 논점 제시",
#             "impact": {
#                 "persuasion_increase": progress_increase
#             }
#         }
#     elif game_state.demon_lord_resistance < 50 and game_state.demon_lord_resistance >= 40:
#         new_plot_point = {
#             "type": "demon_lord_wavering",
#             "chapter": story_progress.current_chapter,
#             "description": "마왕의 결심이 흔들리기 시작함",
#             "impact": {
#                 "resistance_decrease": 50 - game_state.demon_lord_resistance
#             }
#         }
#
#     if new_plot_point:
#         if not isinstance(story_progress.plot_points, list):
#             story_progress.plot_points = []
#         story_progress.plot_points.append(new_plot_point)
#
#     # 게임 종료 조건 확인
#     is_completed = current_turn >= MAX_TURNS
#     result = None
#
#     if is_completed:
#         if game_state.player_persuasion_level > game_state.demon_lord_resistance:
#             result = "victory"
#         else:
#             result = "defeat"
#
#     # 스토리 분기 처리
#     if story_progress.current_chapter == 3:
#         if "동맹" in dialogue_analysis['used_keywords']:
#             story_progress.story_path = "alliance"
#         elif "대결" in dialogue_analysis['used_keywords']:
#             story_progress.story_path = "confrontation"
#         else:
#             story_progress.story_path = "neutral"
#
#     story_progress.save()
#
#     return {
#         "current_chapter": story_progress.current_chapter,
#         "progress": story_progress.progress,
#         "plot_points": story_progress.plot_points,
#         "story_path": getattr(story_progress, 'story_path', None),
#         "is_completed": is_completed,
#         "result": result
#     }
def update_persuasion_and_resistance(game_state, player_analysis, dialogue_analysis, calculate_resistance_decrease):
    # 대화 분석 결과를 바탕으로 가중치 계산
    dialogue_score = dialogue_analysis['score']
    message_length = dialogue_analysis['length']

    # 설득력 증가량 계산
    base_persuasion_increase = max(0, player_analysis['persuasion_strength'])
    length_bonus = min(message_length / 100, 0.5)  # 최대 50% 보너스
    score_multiplier = 1 + (dialogue_score / 100)  # 점수에 따라 -100%에서 +100%까지 변동

    persuasion_increase = base_persuasion_increase * (1 + length_bonus) * score_multiplier
    new_persuasion_level = min(100, game_state.player_persuasion_level + persuasion_increase)

    # 악마 군주의 저항력 업데이트
    if calculate_resistance_decrease:
        base_resistance_decrease = calculate_resistance_decrease(player_analysis, game_state)
        resistance_decrease = base_resistance_decrease * score_multiplier
        new_resistance = max(0, game_state.demon_lord_resistance - resistance_decrease)
    else:
        resistance_decrease = 0
        new_resistance = game_state.demon_lord_resistance

    # 새로운 게임 상태 반환
    return {
        'new_persuasion_level': new_persuasion_level,
        'persuasion_increase': persuasion_increase,
        'new_resistance': new_resistance,
        'resistance_decrease': resistance_decrease,
        'dialogue_impact': {
            'score': dialogue_score,
            'length_bonus': length_bonus,
            'score_multiplier': score_multiplier
        }
    }


# 사용 예:
# new_state = update_persuasion_and_resistance(game_state, player_analysis, calculate_resistance_decrease)
# game_state.player_persuasion_level = new_state['new_persuasion_level']
# game_state.demon_lord_resistance = new_state['new_resistance']
def update_emotional_states(game_state, player_analysis, dialogue_analysis):
    try:
        # 입력 검증
        if 'emotional_impact' not in player_analysis or 'persuasion_strength' not in player_analysis:
            raise ValueError("Player analysis is missing required keys")

        dialogue_score = dialogue_analysis['score']

        # 플레이어 감정 상태 업데이트
        base_player_emotion = update_emotional_state(
            game_state.player_emotional_state,
            player_analysis['emotional_impact']
        )
        # 대화 분석 점수에 따른 추가 감정 변화
        player_emotion_adjustment = dialogue_score / 20  # -5에서 +5 사이의 값
        new_player_emotion = max(0, min(100, base_player_emotion + player_emotion_adjustment))

        # 마왕 감정 상태 업데이트
        base_demon_lord_emotion = update_demon_lord_emotion(
            game_state,
            player_analysis['persuasion_strength']
        )
        # 대화 분석 점수에 따른 추가 감정 변화 (마왕은 반대로 반응)
        demon_lord_emotion_adjustment = -dialogue_score / 20  # -5에서 +5 사이의 값
        new_demon_lord_emotion = max(0, min(100, base_demon_lord_emotion + demon_lord_emotion_adjustment))

        # 게임 상태 업데이트
        game_state.player_emotional_state = new_player_emotion
        game_state.demon_lord_emotional_state = new_demon_lord_emotion

        # 업데이트된 감정 상태 반환
        return {
            'player_emotion': new_player_emotion,
            'demon_lord_emotion': new_demon_lord_emotion,
            'player_emotion_change': new_player_emotion - game_state.player_emotional_state,
            'demon_lord_emotion_change': new_demon_lord_emotion - game_state.demon_lord_emotional_state
        }

    except Exception as e:
        logger.error(f"감정 상태 업데이트 중 오류 발생: {str(e)}")
        # 에러 발생 시 원래의 감정 상태 반환
        return {
            'player_emotion': game_state.player_emotional_state,
            'demon_lord_emotion': game_state.demon_lord_emotional_state,
            'player_emotion_change': 0,
            'demon_lord_emotion_change': 0
        }


def update_argument_strength(game_state, player_analysis, dialogue_analysis):
    try:
        # 입력 검증
        if 'primary_approach' not in player_analysis:
            raise ValueError("Player analysis is missing 'primary_approach' key")

        # 기본 논점 강도 계산
        base_argument_strength = calculate_argument_strength(
            game_state.player_persuasion_level,
            game_state.demon_lord_resistance,
            player_analysis['primary_approach']
        )

        # 대화 분석 결과를 반영한 보정
        dialogue_score = dialogue_analysis['score']
        used_keywords = dialogue_analysis['used_keywords']

        # 키워드 사용에 따른 보너스 계산
        keyword_bonus = sum(used_keywords.values()) * 0.5  # 각 키워드당 0.5점 보너스

        # 대화 점수에 따른 승수 계산 (0.5 ~ 1.5)
        score_multiplier = 1 + (dialogue_score / 200)

        # 최종 논점 강도 계산
        new_argument_strength = (base_argument_strength + keyword_bonus) * score_multiplier

        # 0에서 100 사이로 제한
        new_argument_strength = max(0, min(100, new_argument_strength))

        # 게임 상태 업데이트
        game_state.argument_strength = new_argument_strength

        # 업데이트된 논점 강도와 상세 정보 반환
        return {
            'argument_strength': new_argument_strength,
            'base_strength': base_argument_strength,
            'keyword_bonus': keyword_bonus,
            'score_multiplier': score_multiplier
        }

    except Exception as e:
        logger.error(f"논점 강도 업데이트 중 오류 발생: {str(e)}")
        # 에러 발생 시 원래의 논점 강도 반환
        return {
            'argument_strength': game_state.argument_strength,
            'base_strength': game_state.argument_strength,
            'keyword_bonus': 0,
            'score_multiplier': 1
        }


# def check_game_completion(game_session: GameSession, game_state: GameState) -> Tuple[bool, Dict]:
#     is_completed = False
#     result = {}
#
#     try:
#         if game_state.player_persuasion_level >= 100:
#             is_completed = True
#             result = {'outcome': '설득 승리', 'description': '플레이어가 마왕을 완전히 설득했습니다!'}
#         elif game_state.demon_lord_resistance <= 0:
#             is_completed = True
#             result = {'outcome': '저항 무력화 승리', 'description': '마왕의 저항이 완전히 무너졌습니다!'}
#         elif game_state.player_persuasion_level >= 90 and game_session.storyprogress.current_chapter >= 5:
#             is_completed = True
#             result = {'outcome': '완벽한 엔딩', 'description': '플레이어가 마왕과의 대화에서 탁월한 성과를 거두었습니다!'}
#         elif (timezone.now() - game_session.start_time).total_seconds() > 3600:  # 1시간 제한
#             is_completed = True
#             result = {'outcome': '시간 초과', 'description': '제한 시간 내에 마왕을 설득하지 못했습니다.'}
#         elif game_session.dialogues.count() > 50:  # 대화 턴 수 제한
#             is_completed = True
#             result = {'outcome': '대화 턴 초과', 'description': '너무 많은 대화를 나누어 마왕이 지쳤습니다.'}
#
#         if is_completed:
#             end_game(game_session, result['outcome'])
#
#         return is_completed, result
#
#     except Exception as e:
#         logger.error(f"게임 종료 조건 확인 중 오류 발생: {str(e)}")
#         return False, {'outcome': '오류', 'description': '게임 종료 조건 확인 중 오류가 발생했습니다.'}

def end_game(game_session: GameSession, result: str) -> None:
    try:
        game_session.is_active = False
        game_session.is_completed = True
        end_time = timezone.now()
        game_session.end_time = end_time
        game_session.result = result
        game_session.save()

        # 최종 게임 상태 저장
        GameResult.objects.create(
            game_session=game_session,
            result=result,
            final_persuasion_level=game_session.gamestate.player_persuasion_level,
            final_demon_resistance=game_session.gamestate.demon_lord_resistance,
            final_chapter=game_session.storyprogress.current_chapter,
            total_turns=game_session.dialogues.count(),
            duration=end_time - game_session.start_time
        )

        logger.info(f"게임 종료 처리 완료. 세션 ID: {game_session.id}, 결과: {result}")

    except Exception as e:
        logger.error(f"게임 종료 처리 중 오류 발생. 세션 ID: {game_session.id}, 오류: {str(e)}")

def check_game_end(game_session) -> Tuple[bool, Dict]:
    try:
        game_state = game_session.gamestate
        story_progress = game_session.storyprogress

        end_conditions = [
            ('설득 승리', lambda: game_state.player_persuasion_level >= 100,
             '플레이어가 마왕을 완전히 설득했습니다!'),
            ('저항 무력화', lambda: game_state.demon_lord_resistance <= 0,
             '마왕의 저항이 완전히 무너졌습니다!'),
            ('완벽한 엔딩', lambda: story_progress.current_chapter >= 5 and game_state.player_persuasion_level >= 90,
             '플레이어가 마왕과의 대화에서 탁월한 성과를 거두었습니다!'),
            ('시간 초과', lambda: (timezone.now() - game_session.start_time).total_seconds() > 3600,
             '제한 시간 내에 마왕을 설득하지 못했습니다.'),
            ('대화 턴 초과', lambda: game_session.dialogues.count() > 50,
             '너무 많은 대화를 나누어 마왕이 지쳤습니다.'),
            ('스토리 기반 엔딩', lambda: 'game_over_event' in story_progress.plot_points,
             '스토리의 특정 이벤트로 인해 게임이 종료되었습니다.')
        ]

        for result, condition, description in end_conditions:
            if condition():
                end_game(game_session, result)
                logger.info(f"게임 종료: {result} - {description}")
                return True, {'result': result, 'description': description}

        return False, {}

    except AttributeError as e:
        error_msg = "게임 상태나 진행 상황 정보가 없습니다."
        logger.error(f"게임 종료 확인 중 오류 발생: {error_msg} - {str(e)}")
        end_game(game_session, '오류')
        return True, {'result': '오류', 'description': error_msg}

    except Exception as e:
        error_msg = "게임 종료 확인 중 예기치 못한 오류가 발생했습니다."
        logger.exception(f"게임 종료 확인 중 예외 발생: {str(e)}")
        end_game(game_session, '오류')
        return True, {'result': '오류', 'description': error_msg}


@login_required
def game_result(request, game_session_id):
    game_session = get_object_or_404(GameSession, id=game_session_id)

    # 권한 확인
    if game_session.player.user != request.user:
        return HttpResponseForbidden("이 게임 결과를 볼 수 있는 권한이 없습니다.")

    # 게임 완료 확인
    if not game_session.is_completed:
        return HttpResponseForbidden("이 게임은 아직 완료되지 않았습니다.")

    # GameResult 가져오기
    try:
        game_result = game_session.game_result
    except GameResult.DoesNotExist:
        # GameResult가 없는 경우 처리 (예: 이전 버전에서 생성된 게임 세션)
        game_result = None

    # 대화 내용 가져오기
    dialogues = game_session.dialogues.order_by('timestamp')

    # 대화 내용 페이지네이션
    dialogues = game_session.dialogues.order_by('timestamp')
    paginator = Paginator(dialogues, 20)  # 페이지당 20개의 대화 표시
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'game_session': game_session,
        'game_result': game_result,
        'dialogues': dialogues,
        'final_state': game_session.gamestate,
        'story_progress': game_session.storyprogress,
        'total_turns': game_result.total_turns,
        'game_duration': game_result.duration,
    }
    return render(request, 'game/result.html', context)
def play_game_sheet(request, game_session_id):
    game_session = get_object_or_404(GameSession, id=game_session_id)

    context = {
        'game_session': game_session,
        'game_state': game_session.gamestate,
        'story_progress': game_session.storyprogress,
    }

    return render(request, 'game/gamesheet.html', context)
