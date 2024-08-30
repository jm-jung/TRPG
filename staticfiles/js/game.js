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

    var form = document.getElementById('game-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            }).then(function(response) {
                return response.text();  // Change this line from json() to text()
            }).then(function(data) {
                try {
                    var jsonData = JSON.parse(data);
                    if (jsonData.redirect) {
                        window.location.href = jsonData.redirect;
                    } else if (jsonData.html) {
                        document.body.innerHTML = jsonData.html;
                        // 페이지 업데이트 후 JavaScript 재실행
                        var scripts = document.getElementsByTagName('script');
                        for (var i = 0; i < scripts.length; i++) {
                            if (scripts[i].src) {
                                var script = document.createElement('script');
                                script.src = scripts[i].src;
                                document.body.appendChild(script);
                            }
                        }
                    }
                } catch (e) {
                    // If parsing as JSON fails, treat it as HTML
                    document.body.innerHTML = data;
                    // 페이지 업데이트 후 JavaScript 재실행
                    var scripts = document.getElementsByTagName('script');
                    for (var i = 0; i < scripts.length; i++) {
                        if (scripts[i].src) {
                            var script = document.createElement('script');
                            script.src = scripts[i].src;
                            document.body.appendChild(script);
                        }
                    }
                }
            }).catch(function(error) {
                console.error('Error:', error);
            });
        });
    }
});

function submitAction(action, abilityId = null) {
    var actionInput = document.getElementById('action-input');
    var abilityIdInput = document.getElementById('ability-id-input');

    actionInput.value = action;
    abilityIdInput.value = abilityId !== null ? abilityId : '';

    document.getElementById('game-form').dispatchEvent(new Event('submit'));
}