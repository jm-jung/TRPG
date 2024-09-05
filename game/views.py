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
from .models import  Player, GameSession, Dialogue, GameState,StoryProgress
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from .game_logic import update_emotional_state, update_demon_lord_emotion, calculate_argument_strength, \
    update_environmental_factors
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
        return render(request, 'game/play.html', {'game_session': game_session})


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
        '파괴': -4
    }

    # 감정 표현 패턴 (예시)
    emotion_patterns = {
        r'\b기쁘|즐겁|행복': 3,
        r'\b슬프|우울|속상': -2,
        r'\b화나|짜증|분노': -3,
        r'\b두렵|무서': -2,
        r'\b감사|고마': 4
    }

    score = 0
    used_keywords = Counter()

    # 키워드 분석
    for word, value in keywords.items():
        count = message.count(word)
        score += count * value
        if count > 0:
            used_keywords[word] = count

    # 감정 표현 분석
    for pattern, value in emotion_patterns.items():
        if re.search(pattern, message):
            score += value

    return {
        'score': score,
        'used_keywords': dict(used_keywords),
        'length': len(message)
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

        # 플레이어 대화 저장
        Dialogue.objects.create(
            game_session=game_session,
            speaker='영웅',
            content=player_message
        )

        # AI를 사용하여 마왕의 응답 생성
        demon_lord_response = generate_demon_lord_response(player_message, game_session.gamestate,
                                                           game_session.storyprogress)

        # 마왕 대화 저장
        Dialogue.objects.create(
            game_session=game_session,
            speaker='마왕',
            content=demon_lord_response
        )

        # 게임 상태 및 스토리 진행 업데이트 (대화 분석 결과 포함)
        update_game_state(game_session, player_message, demon_lord_response, dialogue_analysis)
        update_story_progress(game_session, dialogue_analysis)

        # 게임 종료 조건 확인
        game_end_result = check_game_end(game_session)
        is_game_ended = bool(game_end_result)
        if is_game_ended:
            end_game(game_session, game_end_result)

        # 응답 데이터 준비
        response_data = {
            'demon_lord_response': demon_lord_response,
            'game_state': {
                'player_persuasion_level': game_session.player.persuasion_level,
                'player_emotional_state': game_session.player_emotional_state,
                'demon_lord_resistance': game_session.demon_lord_resistance,
                'demon_lord_emotional_state': game_session.demon_lord_emotional_state,
                'argument_strength': game_session.argument_strength,
            },
            'story_progress': {
                'current_chapter': game_session.storyprogress.current_chapter,
                'chapter_progress': game_session.storyprogress.chapter_progress,
            },
            'dialogue_analysis': dialogue_analysis,
            'is_game_ended': is_game_ended,
            'game_result': game_end_result if is_game_ended else None
        }

        logger.info(f"대화가 처리되었습니다. 게임 세션: {game_session_id}")
        return JsonResponse(response_data)

    except Exception as e:
        logger.exception(f"대화 처리 중 오류 발생. 게임 세션 {game_session_id}: {str(e)}")
        return JsonResponse({'error': "대화 처리 중 예기치 못한 오류가 발생했습니다."}, status=500)


# update_game_state와 update_story_progress 함수도 dialogue_analysis 매개변수를 받도록 수정해야 합니다.
def update_game_state(
        game_session: GameSession,
        player_message: str,
        story_progress: StoryProgress,
        calculate_resistance_decrease: Optional[Callable] = None
) -> Tuple[Optional[GameState], Optional[str], bool, Dict]:
    try:
        with transaction.atomic():
            game_state = game_session.gamestate

            # 플레이어 메시지 분석
            player_analysis = analyze_player_message(player_message)
            logger.info(f"플레이어 메시지 분석 완료. 게임 세션 ID: {game_session.id}")

            # 대화 내용 분석
            dialogue_analysis = analyze_dialogue_content(player_message)
            logger.info(f"대화 내용 분석 완료. 게임 세션 ID: {game_session.id}")

            # 악마 군주의 응답 생성
            demon_lord_response = generate_demon_lord_response(player_message, game_state, story_progress)
            logger.info(f"악마 군주 응답 생성 완료. 게임 세션 ID: {game_session.id}")

            # 게임 상태 업데이트
            persuasion_resistance_update = update_persuasion_and_resistance(
                game_state, player_analysis, dialogue_analysis, calculate_resistance_decrease
            )
            emotional_states_update = update_emotional_states(game_state, player_analysis, dialogue_analysis)
            argument_strength_update = update_argument_strength(game_state, player_analysis, dialogue_analysis)
            environmental_factors_update = update_environmental_factors(game_state.environmental_factors,
                                                                        player_message)

            logger.info(f"게임 상태 업데이트 완료. 게임 세션 ID: {game_session.id}")

            # 게임 종료 조건 확인
            is_game_over, game_result = check_game_completion(game_session, game_state)

            game_state.save()
            logger.info(f"게임 상태 저장 완료. 게임 세션 ID: {game_session.id}")

            # 업데이트 결과 종합
            update_results = {
                'persuasion_resistance': persuasion_resistance_update,
                'emotional_states': emotional_states_update,
                'argument_strength': argument_strength_update,
                'environmental_factors': environmental_factors_update,
                'dialogue_analysis': dialogue_analysis
            }

            if is_game_over:
                logger.info(f"게임 종료. 세션 ID: {game_session.id}, 결과: {game_result}")
                return None, "게임이 종료되었습니다.", True, update_results

            return game_state, demon_lord_response, False, update_results

    except ValidationError as ve:
        logger.error(f"유효성 검사 오류 발생. 게임 세션 ID {game_session.id}: {str(ve)}")
        return None, f"유효성 검사 오류: {str(ve)}", False, {}
    except Exception as e:
        logger.exception(f"예기치 못한 오류 발생. 게임 세션 ID {game_session.id}: {str(e)}")
        return None, f"게임 상태 업데이트 중 오류 발생: {str(e)}", False, {}

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
def check_game_completion(game_session: GameSession, game_state: GameState) -> Tuple[bool, Dict]:
    is_completed = False
    result = {}

    try:
        if game_state.player_persuasion_level >= 100:
            is_completed = True
            result = {'outcome': '설득 승리', 'description': '플레이어가 마왕을 완전히 설득했습니다!'}
        elif game_state.demon_lord_resistance <= 0:
            is_completed = True
            result = {'outcome': '저항 무력화 승리', 'description': '마왕의 저항이 완전히 무너졌습니다!'}
        elif game_state.player_persuasion_level >= 90 and game_session.storyprogress.current_chapter >= 5:
            is_completed = True
            result = {'outcome': '완벽한 엔딩', 'description': '플레이어가 마왕과의 대화에서 탁월한 성과를 거두었습니다!'}
        elif (timezone.now() - game_session.start_time).total_seconds() > 3600:  # 1시간 제한
            is_completed = True
            result = {'outcome': '시간 초과', 'description': '제한 시간 내에 마왕을 설득하지 못했습니다.'}
        elif game_session.dialogues.count() > 50:  # 대화 턴 수 제한
            is_completed = True
            result = {'outcome': '대화 턴 초과', 'description': '너무 많은 대화를 나누어 마왕이 지쳤습니다.'}

        if is_completed:
            end_game(game_session, result['outcome'])

        return is_completed, result

    except Exception as e:
        logger.error(f"게임 종료 조건 확인 중 오류 발생: {str(e)}")
        return False, {'outcome': '오류', 'description': '게임 종료 조건 확인 중 오류가 발생했습니다.'}
@transaction.atomic
def update_story_progress(game_session, player_message, demon_lord_response):
    story_progress = game_session.storyprogress
    game_state = game_session.gamestate

    # 현재 챕터 업데이트
    if game_state.player_persuasion_level >= story_progress.next_chapter_threshold:
        story_progress.current_chapter += 1
        story_progress.next_chapter_threshold += 20  # 다음 챕터로 넘어가기 위한 설득력 임계값 증가

    # 주요 플롯 포인트 추가
    if "특정 키워드" in player_message or "특정 키워드" in demon_lord_response:
        story_progress.plot_points.append({
            "chapter": story_progress.current_chapter,
            "event": "주요 사건 설명",
            "player_persuasion": game_state.player_persuasion_level,
            "demon_resistance": game_state.demon_lord_resistance
        })

    # 스토리 분기 처리
    if story_progress.current_chapter == 3 and "선택적 키워드" in player_message:
        story_progress.story_path = "A"  # 스토리 경로 A 선택
    elif story_progress.current_chapter == 3:
        story_progress.story_path = "B"  # 스토리 경로 B 선택

    # 엔딩 조건 확인
    if story_progress.current_chapter >= 5 and game_state.player_persuasion_level >= 90:
        game_session.is_completed = True
        game_session.result = "perfect_ending"
    elif game_state.player_persuasion_level >= 100 or game_state.demon_lord_resistance <= 0:
        game_session.is_completed = True
        game_session.result = "good_ending"

    story_progress.save()
    game_session.save()

    return {
        "current_chapter": story_progress.current_chapter,
        "story_path": story_progress.story_path,
        "is_completed": game_session.is_completed,
        "result": game_session.result
    }

def end_game(game_session: GameSession, result: str) -> None:
    try:
        game_session.is_active = False
        game_session.is_completed = True
        game_session.end_time = timezone.now()
        game_session.result = result
        game_session.save()

        # 게임 종료 시 추가 작업
        final_state = game_session.gamestate
        story_progress = game_session.storyprogress

        # 최종 게임 상태 저장 (예: 별도의 GameResult 모델이 있다고 가정)

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

    # 대화 내용 페이지네이션
    dialogues = game_session.dialogues.order_by('timestamp')
    paginator = Paginator(dialogues, 20)  # 페이지당 20개의 대화 표시
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 게임 종료 이유 결정
    end_reason = check_game_end(game_session)

    context = {
        'game_session': game_session,
        'dialogues': page_obj,
        'final_state': game_session.gamestate,
        'story_progress': game_session.storyprogress,
        'end_reason': end_reason,
        'total_turns': game_session.dialogues.count(),
        'game_duration': (game_session.end_time - game_session.start_time).total_seconds() // 60,  # 분 단위
    }
    return render(request, 'game/result.html', context)