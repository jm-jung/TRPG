from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
from django.conf import settings
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 모델과 토크나이저를 전역 변수로 선언
model = None
tokenizer = None
sentiment_analyzer = None

def load_model():
    global model, tokenizer, sentiment_analyzer
    if model is None or tokenizer is None:
        model_name = "skt/kogpt2-base-v2"  # 한국어 모델로 변경
        sentiment_model_name = "snunlp/KR-FinBert-SC"  # 한국어 감정 분석 모델
        try:
            model = AutoModelForCausalLM.from_pretrained(model_name).eval()
            model.to('cuda' if torch.cuda.is_available() else 'cpu')
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            sentiment_analyzer = pipeline("sentiment-analysis", model=sentiment_model_name, tokenizer=sentiment_model_name)
            logger.info(f"모델 {model_name}와 {sentiment_model_name}이 성공적으로 로드되었습니다.")
        except Exception as e:
            logger.error(f"모델 로딩 중 오류 발생: {e}")
            raise

@torch.no_grad()
def generate_demon_lord_response(player_message, game_state, story_progress):
    global model, tokenizer

    load_model()

    context = f"""
    당신은 텍스트 기반 RPG의 마왕입니다. 플레이어는 설득과 조종을 통해 당신을 물리치려 하고 있습니다.
    현재 게임 상태:
    - 당신의 저항력: {game_state.demon_lord_resistance}/100
    - 당신의 감정 상태: {game_state.demon_lord_emotional_state}
    - 플레이어의 설득력: {game_state.player_persuasion_level}/100
    - 플레이어의 감정 상태: {game_state.player_emotional_state}
    - 현재 논점의 강도: {game_state.argument_strength}
    - 스토리 진행: 챕터 {story_progress.current_chapter}

    마왕으로서 현재 상태와 플레이어의 접근 방식을 고려하여 응답하세요.
    교활하고, 자부심 강하며, 조종에 저항적이어야 하지만, 강력한 논리나 감정적 호소에 미묘하게 영향을 받는 모습도 보이세요.
    당신의 응답은 감정 상태와 저항 수준을 반영해야 합니다.

    플레이어: {player_message}
    마왕:
    """

    input_ids = tokenizer.encode(context, return_tensors="pt").to(model.device)

    try:
        output = model.generate(
            input_ids,
            max_length=len(input_ids[0]) + 100,  # 한국어는 더 긴 텍스트가 필요할 수 있으므로 길이 증가
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            temperature=0.7,
            top_k=50,
            top_p=0.95,
        )
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        return response.split("마왕:")[-1].strip()
    except Exception as e:
        logger.error(f"AI 응답 생성 중 오류 발생: {e}")
        return "마왕이 침묵을 지키며 당신을 의심스럽게 바라봅니다."

def analyze_player_message(message):
    load_model()

    try:
        sentiment = sentiment_analyzer(message)[0]

        # 감정 분석 결과를 바탕으로 emotional_impact 결정
        if sentiment['label'] == 'positive' and sentiment['score'] > 0.7:
            emotional_impact = "매우 긍정적"
        elif sentiment['label'] == 'positive':
            emotional_impact = "긍정적"
        elif sentiment['label'] == 'negative' and sentiment['score'] > 0.7:
            emotional_impact = "매우 부정적"
        elif sentiment['label'] == 'negative':
            emotional_impact = "부정적"
        else:
            emotional_impact = "중립적"

        # 키워드 기반 분석 (한국어로 변경)
        persuasion_keywords = ['부탁드립니다', '고려해주세요', '이해해주세요', '생각해보세요']
        threat_keywords = ['조심하세요', '위험합니다', '위협', '결과']

        persuasion_strength = sum(keyword in message for keyword in persuasion_keywords)
        threat_level = sum(keyword in message for keyword in threat_keywords)

        if persuasion_strength > threat_level:
            approach = '설득'
            strength = min(persuasion_strength, 10)
        else:
            approach = '위협'
            strength = min(threat_level, 10)

        return {
            "persuasion_strength": strength,
            "emotional_impact": emotional_impact,
            "primary_approach": approach
        }
    except Exception as e:
        logger.error(f"플레이어 메시지 분석 중 오류 발생: {e}")
        return {
            "persuasion_strength": 0,
            "emotional_impact": "중립적",
            "primary_approach": "알 수 없음"
        }