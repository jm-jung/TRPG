# game/game_logic.py

from django.utils import timezone
from .models import GameSession, GameState, StoryProgress, Dialogue
from .chatbot import analyze_player_message

def update_emotional_state(current_state, emotional_impact):
    # 감정 상태 업데이트 로직
    # 예시: 간단한 가중 평균
    weight = 0.7
    new_state = current_state * weight + emotional_impact * (1 - weight)
    return max(min(new_state, 100), 0)  # 0에서 100 사이의 값으로 제한

def update_demon_lord_emotion(game_state, persuasion_strength):
    # 마왕의 감정 상태 업데이트 로직
    # 예시: 저항력에 반비례하여 감정 변화
    emotion_change = persuasion_strength * (1 - game_state.demon_lord_resistance / 100)
    new_emotion = game_state.demon_lord_emotional_state + emotion_change
    return max(min(new_emotion, 100), 0)  # 0에서 100 사이의 값으로 제한

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

def update_game_state(game_session, player_message, demon_lord_response):
    game_state = game_session.gamestate
    story_progress = game_session.storyprogress

    # 플레이어 메시지 분석 (chatbot.py의 함수 사용)
    player_analysis = analyze_player_message(player_message)

    # 게임 상태 업데이트
    game_state.player_persuasion_level = min(100, game_state.player_persuasion_level + player_analysis['persuasion_strength'])
    game_state.demon_lord_resistance = max(0, game_state.demon_lord_resistance - player_analysis['persuasion_strength'])
    game_state.player_emotional_state = update_emotional_state(game_state.player_emotional_state, player_analysis['emotional_impact'])
    game_state.demon_lord_emotional_state = update_demon_lord_emotion(game_state, player_analysis['persuasion_strength'])
    game_state.argument_strength = calculate_argument_strength(
        game_state.player_persuasion_level,
        game_state.demon_lord_resistance,
        player_analysis['primary_approach']
    )

    # 환경 요인 업데이트
    game_state.environmental_factors = update_environmental_factors(game_state.environmental_factors, player_message)

    game_state.save()

    # 스토리 진행 업데이트
    update_story_progress(story_progress, game_state, player_analysis)

    return game_state

def update_story_progress(story_progress, game_state, player_analysis):
    # 스토리 진행 업데이트 로직
    if game_state.player_persuasion_level >= story_progress.next_chapter_threshold:
        story_progress.current_chapter += 1
        story_progress.next_chapter_threshold += 20

    # 주요 플롯 포인트 추가 (예시)
    if "평화" in player_analysis['content'] or "협력" in player_analysis['content']:
        story_progress.plot_points.append({
            "chapter": story_progress.current_chapter,
            "event": "플레이어가 평화적 해결책 제안",
            "player_persuasion": game_state.player_persuasion_level,
            "demon_resistance": game_state.demon_lord_resistance
        })

    story_progress.save()

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