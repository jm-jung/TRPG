document.addEventListener('DOMContentLoaded', function() {
    const sendButton = document.getElementById('send-message');
    const playerInput = document.getElementById('player-message');
    const dialogueContent = document.getElementById('dialogue-content');

    sendButton.addEventListener('click', sendMessage);
    playerInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

  function sendMessage(message) {
    // URL 구성 방식 변경
        const url = new URL(`/api/process-dialogue/${gameSessionId}/`, window.location.origin);

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `message=${encodeURIComponent(message)}`
        })
            .then(response => response.json())
            .then(data => {
                updateDialogue(message, data.demon_lord_response);
                updateGameState(data.game_state);
                checkGameEnd(data.game_state.is_game_ended, data.game_state.game_result);
            })
            .catch(error => console.error('Error:', error));

            playerInput.value = '';
  }

    function updateDialogue(playerMessage, demonLordResponse) {
        dialogueContent.innerHTML += `<p><strong>플레이어:</strong> ${playerMessage}</p>`;
        dialogueContent.innerHTML += `<p><strong>마왕:</strong> ${demonLordResponse}</p>`;
        dialogueContent.scrollTop = dialogueContent.scrollHeight;
    }

    function updateGameState(gameState) {
        document.getElementById('current-turn').textContent = gameState.current_chapter;
        document.getElementById('player-persuasion').textContent = gameState.player_persuasion_level;
        document.getElementById('demon-resistance').textContent = gameState.demon_lord_resistance;
        document.getElementById('player-emotion').textContent = gameState.player_emotional_state;
        document.getElementById('demon-emotion').textContent = gameState.demon_lord_emotional_state;
        document.getElementById('argument-strength').textContent = gameState.argument_strength;

        updateProgressBar(gameState.current_chapter);
    }

    function updateProgressBar(currentChapter) {
        const totalChapters = 10; // 총 챕터 수
        const progress = (currentChapter / totalChapters) * 100;
        document.getElementById('progress-fill').style.width = `${progress}%`;
        document.getElementById('progress-text').textContent = `${Math.round(progress)}%`;
    }

    function checkGameEnd(isGameEnded, gameResult) {
        if (isGameEnded) {
            alert(`게임이 종료되었습니다. 결과: ${gameResult}`);
            // 여기에 게임 종료 후 처리 로직 추가
        }
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});