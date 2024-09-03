from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from django.conf import settings
import os

# 모델과 토크나이저를 전역 변수로 선언
model = None
tokenizer = None


def load_model():
    global model, tokenizer
    model_name = "distilgpt2"
    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)


def generate_demon_lord_response(player_message, game_state, story_progress):
    global model, tokenizer

    # 모델이 로드되지 않았다면 로드
    if model is None or tokenizer is None:
        load_model()

    context = f"""
    You are the Demon Lord in a text-based RPG. The player is trying to defeat you through persuasion and manipulation.
    Current game state:
    - Your resistance: {game_state.demon_lord_resistance}/100
    - Your emotional state: {game_state.demon_lord_emotional_state}
    - Player's persuasion level: {game_state.player_persuasion_level}/100
    - Player's emotional state: {game_state.player_emotional_state}
    - Current argument strength: {game_state.argument_strength}
    - Story progress: Chapter {story_progress.current_chapter}

    Respond as the Demon Lord would, considering your current state and the player's approach.
    Be cunning, proud, and resistant to manipulation, but also show subtle signs of being affected by strong arguments or emotional appeals.
    Your response should reflect your emotional state and resistance level.

    Player: {player_message}
    Demon Lord:
    """

    input_ids = tokenizer.encode(context, return_tensors="pt")

    try:
        output = model.generate(
            input_ids,
            max_length=len(input_ids[0]) + 50,  # context length + 50 tokens for response
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            temperature=0.7,
            top_k=50,
            top_p=0.95,
        )
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        return response.split("Demon Lord:")[-1].strip()
    except Exception as e:
        print(f"Error in generating AI response: {e}")
        return "The Demon Lord remains silent, eyeing you suspiciously."


def analyze_player_message(message):
    # 이 함수는 필요에 따라 구현할 수 있습니다.
    # 예를 들어, 간단한 키워드 기반 분석을 수행할 수 있습니다.
    persuasion_keywords = ['please', 'consider', 'understand', 'think about']
    threat_keywords = ['beware', 'danger', 'threat', 'consequences']

    persuasion_strength = sum(keyword in message.lower() for keyword in persuasion_keywords)
    threat_level = sum(keyword in message.lower() for keyword in threat_keywords)

    if persuasion_strength > threat_level:
        approach = 'persuasion'
        strength = min(persuasion_strength, 10)
    else:
        approach = 'threat'
        strength = min(threat_level, 10)

    return {
        "persuasion_strength": strength,
        "emotional_impact": "neutral",  # 이 부분은 더 복잡한 감정 분석 로직으로 대체할 수 있습니다
        "primary_approach": approach
    }