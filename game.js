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
        const sanitizeMessage = (msg) => {
            if (typeof msg !== 'string') {
                console.warn('Expected string for message, got:', typeof msg);
                return String(msg); // 문자열로 변환 시도
            }
            return msg.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;')
                      .replace(/'/g, '&#039;');
        };
        messagesContainer.innerHTML += `
            <div class="message player-message"><strong>영웅:</strong>${sanitizeMessage(playerMessage)}</div>
            <div class="message demon-lord-message"><strong>마왕:</strong> ${sanitizeMessage(demonLordResponse)}</div>
        `;
        dialogueHistory.scrollTop = dialogueHistory.scrollHeight;
    }

    function updateGameState(gameState) {
        if (!gameState) {
            console.error('Invalid game state data received');
            return;
        }

        const updateElement = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value || 'N/A';
            } else {
                console.warn(`Element with id '${id}' not found`);
            }
        };

        updateElement('current-chapter', gameState.story_progress?.current_chapter);
        updateElement('player-persuasion', gameState.player_persuasion_level);
        updateElement('player-emotion', gameState.player_emotional_state);
        updateElement('demon-resistance', gameState.demon_lord_resistance);
        updateElement('demon-emotion', gameState.demon_lord_emotional_state);
        updateElement('argument-strength', gameState.argument_strength);

        console.log('Game state updated:', gameState);
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