document.addEventListener('DOMContentLoaded', function() {
    function updateHealthBar(character, health, maxHealth) {
        var healthBar = document.getElementById(character + '-health-bar');
        if (healthBar) {
            var healthPercentage = (health / maxHealth) * 100;
            healthBar.style.width = healthPercentage + '%';
            healthBar.textContent = health + '/' + maxHealth;
        }
    }

    if (typeof window.heroHealth !== 'undefined' && typeof window.heroMaxHealth !== 'undefined') {
        updateHealthBar('hero', window.heroHealth, window.heroMaxHealth);
    }
    if (typeof window.demonLordHealth !== 'undefined' && typeof window.demonLordMaxHealth !== 'undefined') {
        updateHealthBar('demon-lord', window.demonLordHealth, window.demonLordMaxHealth);
    }
});

function submitAction(action, abilityId = null) {
    var form = document.getElementById('game-form');
    var actionInput = document.getElementById('action-input');
    var abilityIdInput = document.getElementById('ability-id-input');

    actionInput.value = action;
    if (abilityId !== null) {
        abilityIdInput.value = abilityId;
    } else {
        abilityIdInput.value = '';
    }

    var formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    }).then(function(response) {
        return response.json();  // JSON 응답을 파싱
    }).then(function(data) {
        if (data.game_over) {
            // 게임이 종료되었을 경우 결과 페이지로 리다이렉트
            window.location.href = data.redirect_url;
        } else {
            // 게임이 진행 중일 경우 상태 업데이트
            updateGameState(data);
        }
    }).catch(function(error) {
        console.error('Error:', error);
    });
}

function updateGameState(data) {
    // 게임 상태 업데이트 로직
    if (data.hero) {
        updateHealthBar('hero', data.hero.health, data.hero.max_health);
    }
    if (data.demon_lord) {
        updateHealthBar('demon-lord', data.demon_lord.health, data.demon_lord.max_health);
    }

    // 행동 로그 업데이트
    var actionLog = document.getElementById('action-log');
    if (actionLog && data.action_log) {
        actionLog.innerHTML = data.action_log;
    }

    // 기타 필요한 UI 업데이트
    // ...
    function updateGameState(data) {
    // 히어로와 마왕의 체력 업데이트
        if (data.hero) {
            updateHealthBar('hero', data.hero.health, data.hero.max_health);
            document.getElementById('hero-mana').textContent = data.hero.mana + '/' + data.hero.max_mana;
        }
        if (data.demon_lord) {
            updateHealthBar('demon-lord', data.demon_lord.health, data.demon_lord.max_health);
        }

        // 현재 턴 정보 업데이트
        document.getElementById('current-turn').textContent = 'Turn: ' + data.current_turn;

        // 행동 로그 업데이트
        var actionLog = document.getElementById('action-log');
        if (actionLog && data.action_log) {
            // 새로운 액션을 로그의 맨 위에 추가
            var newAction = document.createElement('div');
            newAction.textContent = data.action_log;
            actionLog.insertBefore(newAction, actionLog.firstChild);

            // 로그가 너무 길어지지 않도록 오래된 항목 제거
            if (actionLog.children.length > 5) {
                actionLog.removeChild(actionLog.lastChild);
            }
        }

        // 특수 능력 버튼 상태 업데이트
        if (data.hero.abilities) {
            data.hero.abilities.forEach(function(ability) {
                var abilityButton = document.getElementById('ability-' + ability.id);
                if (abilityButton) {
                    abilityButton.disabled = !ability.is_available;
                    abilityButton.textContent = ability.name + (ability.is_available ? '' : ' (쿨다운)');
                }
            });
        }

        // 캐릭터 상태 효과 표시 (예: 저주)
        var heroStatusEffect = document.getElementById('hero-status-effect');
        if (heroStatusEffect) {
            heroStatusEffect.textContent = data.hero.is_cursed ? '저주 걸림!' : '';
        }

        // 게임 진행 상황 표시 (예: 프로그레스 바)
        var gameProgress = document.getElementById('game-progress');
        if (gameProgress && data.max_turns) {
            var progressPercentage = (data.current_turn / data.max_turns) * 100;
            gameProgress.style.width = progressPercentage + '%';
        }

        // 알림 메시지 표시 (중요한 이벤트 발생 시)
        if (data.notification) {
            showNotification(data.notification);
        }
    }

    function showNotification(message) {
        var notification = document.getElementById('notification');
        if (notification) {
            notification.textContent = message;
            notification.style.display = 'block';
            setTimeout(function() {
                notification.style.display = 'none';
            }, 3000);
        }
    }
}