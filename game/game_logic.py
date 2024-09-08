# game/game_logic.py
import logging

from django.utils import timezone
from .models import GameSession, GameState, StoryProgress, Dialogue
from .chatbot import analyze_player_message, generate_demon_lord_response

logger = logging.getLogger(__name__)
def update_emotional_state(current_state, emotional_impact):
    # 입력값을 float로 변환 시도
    try:
        current_state = float(current_state)
    except (ValueError, TypeError):
        current_state = 0.0  # 변환 실패 시 기본값 사용

    try:
        emotional_impact = float(emotional_impact)
    except (ValueError, TypeError):
        emotional_impact = 0.0  # 변환 실패 시 기본값 사용

    # 감정 상태 업데이트 로직
    weight = 0.7
    new_state = current_state * weight + emotional_impact * (1 - weight)
    return max(min(new_state, 100), 0)  # 0에서 100 사이의 값으로 제한
def update_demon_lord_emotion(game_state, persuasion_strength):
    try:
        demon_lord_resistance = float(game_state.demon_lord_resistance)
    except (ValueError, TypeError, AttributeError):
        demon_lord_resistance = 100.0  # 기본값 설정

    try:
        current_emotion = float(game_state.demon_lord_emotional_state)
    except (ValueError, TypeError, AttributeError):
        current_emotion = 50.0  # 중간 값으로 기본 설정

    try:
        persuasion_strength = float(persuasion_strength)
    except (ValueError, TypeError):
        persuasion_strength = 0.0  # 기본값 설정

    # 마왕의 감정 상태 업데이트 로직
    emotion_change = persuasion_strength * (1 - demon_lord_resistance / 100)
    new_emotion = current_emotion + emotion_change
    return max(min(new_emotion, 100), 0)
def calculate_argument_strength(persuasion_level, resistance, approach):
    # 논점 강도 계산 로직
    base_strength = persuasion_level - resistance

    # 접근 방식에 따른 보정
    approach_bonus = {
        '논리적': 10,
        '감정적': 5,
        '단호한': 0,
        '공감적': 15
    }

    return max(base_strength + approach_bonus.get(approach, 0), 0)


def update_game_state(game_session, player_message, demon_lord_response, dialogue_analysis):
    game_state = game_session.gamestate
    story_progress = game_session.storyprogress

    # 플레이어의 설득력 업
    print("dialogue_analysis['score']", dialogue_analysis)
    persuasion_increase = dialogue_analysis['score']  # 대화 점수를 기반으로 설득력 증가
    game_state.player_persuasion_level = min(100, game_state.player_persuasion_level + persuasion_increase)
    print('game_state.player_persuasion_level', game_state.player_persuasion_level)

    # 마왕의 저항력 업데이트
    resistance_decrease = persuasion_increase # 설득력 증가에 따라 저항력 감소
    game_state.demon_lord_resistance = max(0, game_state.demon_lord_resistance - resistance_decrease)

    # 감정 상태 업데이트
    # game_state.player_emotional_state = (
    #     update_emotional_state(game_state.player_emotional_state, dialogue_analysis['emotion_score']))
    # game_state.demon_lord_emotional_state = update_demon_lord_emotion(game_state, persuasion_increase)

    # 논점 강도 업데이트
    # game_state.argument_strength = calculate_argument_strength(
    #     game_state.player_persuasion_level,
    #     game_state.demon_lord_resistance,
    #     dialogue_analysis['main_topics'][0] if dialogue_analysis['main_topics'] else 'neutral'
    # )

    # 현재 턴(챕터) 업데이트
    # story_progress.current_chapter += 1

    story_progress_result = update_story_progress(story_progress, game_state, dialogue_analysis, demon_lord_response)

    # 게임 종료 조건 확인
    is_game_ended = story_progress_result['is_completed']
    game_result = story_progress_result['result']

    # 변경사항 저장
    game_state.save()
    story_progress.save()

    return {
        "current_chapter": story_progress.current_chapter,
        "player_persuasion_level": round(game_state.player_persuasion_level, 2),
        "player_emotional_state": game_state.player_emotional_state,
        "demon_lord_resistance": round(game_state.demon_lord_resistance, 2),
        "demon_lord_emotional_state": game_state.demon_lord_emotional_state,
        "argument_strength": round(game_state.argument_strength, 2),
        "is_game_ended": is_game_ended,
        "game_result": game_result,
        "story_path": story_progress_result.get('story_path'),
    }

def update_story_progress(story_progress, game_state, dialogue_analysis, demon_lord_response):
    logger.info(f"Updating story progress. Current chapter: {story_progress.current_chapter}, "
                f"Player persuasion: {game_state.player_persuasion_level}, "
                f"Demon lord resistance: {game_state.demon_lord_resistance}")

    MAX_TURNS = 10
    is_completed = False
    result = None

    # 턴 증가
    story_progress.current_chapter += 1
    current_turn = story_progress.current_chapter

    logger.info(f"Turn increased. New turn: {current_turn}")

    # 플레이어의 설득력에 따른 진행도 증가
    progress_increase = game_state.player_persuasion_level
    story_progress.progress += progress_increase
    logger.info(f"Progress increased. New progress: {story_progress.progress}")

    # 마왕의 응답에 대한 간단한 감정 분석
    sentiment = "negative" if any(word in demon_lord_response for word in ["분노", "거부", "저항"]) else "neutral"
    if "동의" in demon_lord_response or "이해" in demon_lord_response:
        sentiment = "positive"

    # 플롯 포인트 추가 및 관리
    new_plot_point = None
    if "평화" in dialogue_analysis['used_keywords'] or "협력" in dialogue_analysis['used_keywords']:
        new_plot_point = {
            "type": "peace_proposal",
            "chapter": story_progress.current_chapter,
            "description": "플레이어가 평화적 해결책 제안",
            "impact": {
                "player_persuasion": game_state.player_persuasion_level,
                "demon_resistance": game_state.demon_lord_resistance
            }
        }
    elif dialogue_analysis['score'] > 50:  # 높은 대화 점수
        new_plot_point = {
            "type": "successful_argument",
            "chapter": story_progress.current_chapter,
            "description": "플레이어가 강력한 논점 제시",
            "impact": {
                "persuasion_increase": progress_increase
            }
        }
    elif game_state.demon_lord_resistance < 50 and game_state.demon_lord_resistance >= 40:
        new_plot_point = {
            "type": "demon_lord_wavering",
            "chapter": story_progress.current_chapter,
            "description": "마왕의 결심이 흔들리기 시작함",
            "impact": {
                "resistance_decrease": 50 - game_state.demon_lord_resistance
            }
        }
    elif sentiment == 'negative':
        new_plot_point = {
            "type": "demon_lord_resistance",
            "chapter": story_progress.current_chapter,
            "description": "마왕이 강하게 저항함",
            "impact": {
                "resistance_increase": 5
            }
        }
    elif sentiment == 'positive':
        new_plot_point = {
            "type": "demon_lord_consideration",
            "chapter": story_progress.current_chapter,
            "description": "마왕이 플레이어의 제안을 고려 중",
            "impact": {
                "resistance_decrease": 5
            }
        }

    if new_plot_point:
        if not isinstance(story_progress.plot_points, list):
            story_progress.plot_points = []
        story_progress.plot_points.append(new_plot_point)

        # 게임 종료 조건 확인
    if current_turn > MAX_TURNS:
        is_completed = True
        result = "victory" if game_state.player_persuasion_level > game_state.demon_lord_resistance else "defeat"
        logger.info(f"Game ended due to max turns reached. Result: {result}")
    elif game_state.player_persuasion_level >= 100:
        is_completed = True
        result = "perfect_victory"
        logger.info("Game ended due to player reaching max persuasion level")
    elif game_state.demon_lord_resistance <= 0:
        is_completed = True
        result = "surrender"
        logger.info("Game ended due to demon lord's resistance reaching zero")

    # 스토리 분기 처리
    if story_progress.current_chapter == 3:
        if "동맹" in dialogue_analysis['used_keywords'] and sentiment == 'positive':
            story_progress.story_path = "alliance"
        elif "대결" in dialogue_analysis['used_keywords'] or sentiment == 'negative':
            story_progress.story_path = "confrontation"
        else:
            story_progress.story_path = "neutral"

    story_progress.save()

    logger.info(f"Story progress update completed. Is game completed: {is_completed}, Result: {result}")

    return {
        "current_chapter": story_progress.current_chapter,
        "progress": story_progress.progress,
        "plot_points": story_progress.plot_points,
        "story_path": getattr(story_progress, 'story_path', None),
        "is_completed": is_completed,
        "result": result
    }
def check_game_end(game_session):
    game_state = game_session.gamestate
    story_progress = game_session.storyprogress

    if game_state.player_persuasion_level >= 100:
        return end_game(game_session, '설득 승리')

    if game_state.demon_lord_resistance <= 0:
        return end_game(game_session, '저항 무력화 승리')

    if story_progress.current_chapter >= 5 and game_state.player_persuasion_level >= 90:
        return end_game(game_session, '완벽한 엔딩')

    if story_progress.current_chapter >= 10:
        return end_game(game_session, '시간 초과 패배')

    return False

def end_game(game_session, result):
    game_session.is_active = False
    game_session.is_completed = True
    game_session.end_time = timezone.now()
    game_session.result = result
    game_session.save()
    return True

def update_environmental_factors(environmental_factors, player_message):
    # 환경 요인 업데이트 로직

    # 시간 경과
    if 'time' not in environmental_factors:
        environmental_factors['time'] = 0
    environmental_factors['time'] += 1

    # 장소 변경 (플레이어 메시지에 따라)
    if "으로 가" in player_message or "로 가" in player_message:
        new_location = player_message.split("으로 가")[-1].split("로 가")[-1].strip()
        environmental_factors['location'] = new_location

    # 특정 키워드에 따른 이벤트 발생
    if "사용" in player_message or "쓰다" in player_message:
        environmental_factors['special_item_used'] = True

    # 날씨 변화 (랜덤 또는 시간에 따라)
    import random
    weather_options = ['맑음', '비', '흐림', '폭풍']
    if random.random() < 0.1:  # 10% 확률로 날씨 변화
        environmental_factors['weather'] = random.choice(weather_options)

    return environmental_factors