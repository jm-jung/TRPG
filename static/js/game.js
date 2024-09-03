document.addEventListener('DOMContentLoaded', function() {
    const dialogueForm = document.getElementById('dialogue-form');
    const dialogueHistory = document.getElementById('dialogue-history');
    const messageInput = document.getElementById('message-input');
    const persuasionTools = document.querySelectorAll('.persuasion-tool');

    persuasionTools.forEach(tool => {
        tool.addEventListener('click', function() {
            const toolType = this.dataset.tool;
            const toolText = {
                'logic': '논리',
                'emotion': '감정',
                'flattery': '아첨',
                'threat': '위협'
            };
            messageInput.value += `[${toolText[toolType]}] `;
            messageInput.focus();
        });
    });

    dialogueForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value;
        if (message.trim() === '') return;

        sendMessage(message);
        messageInput.value = '';
    });

    function sendMessage(message) {
        const url = window.location.href;
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
            updateDialogueHistory(message, data.demon_lord_response);
            updateGameState(data.game_state);
            checkGameEnd(data.game_state);
        })
        .catch(error => console.error('Error:', error));
    }

    function updateDialogueHistory(playerMessage, demonLordResponse) {
        dialogueHistory.innerHTML += `
            <div class="message player-message"><strong>플레이어:</strong> ${playerMessage}</div>
            <div class="message demon-lord-message"><strong>악마 군주:</strong> ${demonLordResponse}</div>
        `;
        dialogueHistory.scrollTop = dialogueHistory.scrollHeight;
    }

    function updateGameState(gameState) {
        document.getElementById('player-persuasion').textContent = gameState.player_persuasion_level;
        document.getElementById('player-emotion').textContent = gameState.player_emotional_state;
        document.getElementById('demon-resistance').textContent = gameState.demon_lord_resistance;
        document.getElementById('demon-emotion').textContent = gameState.demon_lord_emotional_state;
        document.getElementById('argument-strength').textContent = gameState.argument_strength;
    }

    function checkGameEnd(gameState) {
        if (gameState.demon_lord_resistance <= 0 || gameState.player_persuasion_level >= 100) {
            alert('게임 종료! 결과 페이지로 이동합니다...');
            window.location.href = '/game/result/' + getGameSessionId();
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

    function getGameSessionId() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 2];
    }
});