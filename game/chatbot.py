from openai import OpenAI
from django.conf import settings
import logging
import random

logger = logging.getLogger(__name__)

client = OpenAI()

def generate_demon_lord_response(player_message, game_state, story_progress):
    resistance = game_state.demon_lord_resistance

    # 저항력에 따른 마왕의 태도 결정
    if resistance > 80:
        attitude = "매우 적대적이고 거만한"
    elif resistance > 60:
        attitude = "적대적이지만 약간의 의심이 있는"
    elif resistance > 40:
        attitude = "경계하지만 듣는 자세를 가진"
    elif resistance > 20:
        attitude = "약간 동요하고 관심을 보이는"
    else:
        attitude = "설득되기 시작하고 타협을 고려하는"

    prompt = f"""
    You are the Demon Lord in a text-based RPG. Respond to the player's message directly and in character.
    Your current attitude is {attitude}. Adjust your response accordingly.
    Your goal is still world domination, but as your resistance decreases, show more willingness to listen and consider compromise.
    Respond in Korean and keep your response diverse and contextual.

    Current game state:
    - Your resistance: {resistance}/100
    - Your emotional state: {game_state.demon_lord_emotional_state}
    - Player's persuasion level: {game_state.player_persuasion_level}/100
    - Current chapter: {story_progress}

    Previous messages:
    {game_state.previous_messages[-5:] if hasattr(game_state, 'previous_messages') else []}

    Player: {player_message}
    Demon Lord:
    """
    print(prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are a powerful Demon Lord in a text-based RPG. Your attitude changes based on your current resistance level. Respond in Korean."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            n=1,
            stop=None,
            temperature=0.8,
        )

        demon_lord_response = response.choices[0].message.content.strip()
        logger.info(f"Generated response: {demon_lord_response}")

        if len(demon_lord_response) < 10:
            raise ValueError("Generated response is too short")

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        fallback_responses = [
            "네 말따위는 신경 쓰지 않겠다. 세상의 종말은 피할 수 없어.",
            "어리석은 인간이여, 네가 나를 막을 수 있다고 생각하나?",
            "네 노력이 무색하군. 곧 모든 것이 끝날 것이다.",
            "흥미롭군. 하지만 네 말은 결국 허공에 떠다니는 먼지에 불과해.",
            "네가 뭐라고 지껄이든, 나의 계획은 이미 시작되었다."
        ]
        demon_lord_response = random.choice(fallback_responses)

    # 감정 분석 (간단한 버전)
    if resistance > 60:
        sentiment = "negative"
    elif resistance > 30:
        sentiment = "neutral"
    else:
        sentiment = "positive" if "동의" in demon_lord_response or "이해" in demon_lord_response else "neutral"

    # 이전 메시지 저장 (최대 10개)
    if not hasattr(game_state, 'previous_messages'):
        game_state.previous_messages = []
    game_state.previous_messages.append(f"Player: {player_message}")
    game_state.previous_messages.append(f"Demon Lord: {demon_lord_response}")
    game_state.previous_messages = game_state.previous_messages[-10:]

    return demon_lord_response, {"length": len(demon_lord_response), "sentiment": sentiment}
def analyze_player_message(message):
    prompt = f"""
    다음 메시지의 감정과 설득력을 분석하세요:
    "{message}"

    분석 결과를 다음 형식으로 제공하세요:
    - 감정 상태: [매우 긍정적/긍정적/중립적/부정적/매우 부정적]
    - 설득력: [0-10 사이의 숫자]
    - 주요 접근 방식: [설득/위협]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant that analyzes the emotion and persuasiveness of messages."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5,
        )

        # 응답 처리
        generated_text = response.choices[0].message.content

        analysis = response.choices[0].message['content'].strip()

        # 분석 결과 파싱
        emotional_impact = "중립적"
        persuasion_strength = 0
        primary_approach = "알 수 없음"

        for line in analysis.split('\n'):
            if '감정 상태:' in line:
                emotional_impact = line.split(':')[1].strip()
            elif '설득력:' in line:
                persuasion_strength = int(line.split(':')[1].strip())
            elif '주요 접근 방식:' in line:
                primary_approach = line.split(':')[1].strip()

        return {
            "persuasion_strength": persuasion_strength,
            "emotional_impact": emotional_impact,
            "primary_approach": primary_approach
        }
    except Exception as e:
        logger.error(f"플레이어 메시지 분석 중 오류 발생: {e}")
        return {
            "persuasion_strength": 0,
            "emotional_impact": "중립적",
            "primary_approach": "알 수 없음"
        }