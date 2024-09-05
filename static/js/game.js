document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM content loaded');
    const startGameBtn = document.getElementById('start-game-btn');
    if (startGameBtn) {
        console.log('Start game button found');
        startGameBtn.addEventListener('click', function() {
            console.log('Start game button clicked');
            fetch('start/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    redirect: 'follow'
})
.then(response => {
    console.log('Response status:', response.status);
    console.log('Response headers:', response.headers);
    return response.text().then(text => {
        try {
            return JSON.parse(text);
        } catch (e) {
            console.error('Failed to parse response as JSON:', text);
            throw new Error(`Invalid JSON response: ${text}`);
        }
    });
})
.then(data => {
    console.log('Parsed data:', data);
    if (data.status === 'success') {
        window.location.href = `play/${data.game_session_id}/`;
    } else {
        throw new Error(data.message || '게임 시작 중 알 수 없는 오류가 발생했습니다.');
    }
})
.catch(error => {
    console.error('Detailed error:', error);
    alert('게임 시작 중 오류가 발생했습니다. 개발자 도구의 콘솔을 확인해주세요.');
});
        });
    } else {
        console.log('Start game button not found');
    }

    // 기존의 대화 처리 코드는 그대로 유지
    const dialogueForm = document.getElementById('dialogue-form');
    const dialogueHistory = document.getElementById('dialogue-history');
    const messageInput = document.getElementById('player-message');
    const messagesContainer = document.getElementById('messages-container');

    if (dialogueForm) {
        dialogueForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value;
            if (message.trim() === '') return;

            sendMessage(message);
            messageInput.value = '';
        });
    }

    function sendMessage(message) {
        fetch(`/game/api/process-dialogue/${gameSessionId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `message=${encodeURIComponent(message)}`
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            updateDialogueHistory(message, data.demon_lord_response);
            updateGameState(data.game_state);
            checkGameEnd(data.is_game_ended, data.game_result);
        })
        .catch(error => {
            console.error('Detailed error:', error);
            alert('메시지 전송 중 오류가 발생했습니다. 자세한 내용은 콘솔을 확인해주세요.');
        });
    }
    function updateDialogueHistory(playerMessage, demonLordResponse) {
        messagesContainer.innerHTML += `
            <div class="message player-message"><strong>플레이어:</strong> ${playerMessage}</div>
            <div class="message demon-lord-message"><strong>마왕:</strong> ${demonLordResponse}</div>
        `;
        dialogueHistory.scrollTop = dialogueHistory.scrollHeight;
    }

    function updateGameState(gameState) {
        if (!gameState) {
            console.error('Invalid game state data received');
            return;
        }
        document.getElementById('current-chapter').textContent = gameState.current_chapter || 'N/A';
        document.getElementById('current-turn').textContent = gameState.current_turn || 'N/A';
        document.getElementById('player-persuasion').textContent = gameState.player_persuasion_level || 'N/A';
        document.getElementById('player-emotion').textContent = gameState.player_emotional_state || 'N/A';
        document.getElementById('demon-resistance').textContent = gameState.demon_lord_resistance || 'N/A';
        document.getElementById('demon-emotion').textContent = gameState.demon_lord_emotional_state || 'N/A';
        document.getElementById('argument-strength').textContent = gameState.argument_strength || 'N/A';
    }

    function checkGameEnd(isGameEnded, gameResult) {
        if (isGameEnded) {
            alert(`게임 종료! 결과: ${gameResult}`);
            window.location.href = `result/${gameSessionId}/`;
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