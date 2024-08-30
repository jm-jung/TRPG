from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Hero, DemonLord, GameSession, GameAction, SpecialAbility, CharacterAbility
import random
from django.urls import reverse
from django.contrib.auth import logout
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
def home(request):
    return render(request, 'game/home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'game/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def start_game(request):
    hero = Hero.objects.create(name="Hero", player=request.user)
    demon_lord = DemonLord.objects.create(name="Demon Lord")

    # Add abilities
    fireball = SpecialAbility.objects.get_or_create(name="Fireball", mana_cost=30, cooldown=3)[0]
    curse = SpecialAbility.objects.get_or_create(name="Curse", mana_cost=40, cooldown=5)[0]
    heal = SpecialAbility.objects.get_or_create(name="Heal", mana_cost=25, cooldown=2)[0]

    CharacterAbility.objects.create(hero=hero, ability=fireball)
    CharacterAbility.objects.create(hero=hero, ability=heal)
    CharacterAbility.objects.create(demon_lord=demon_lord, ability=curse)

    game_session = GameSession.objects.create(
        player=request.user,
        hero=hero,
        demon_lord=demon_lord
    )
    return redirect('play_game', game_id=game_session.id)

@login_required
def play_game(request, game_id):
    game_session = GameSession.objects.get(id=game_id)
    hero = game_session.hero
    demon_lord = game_session.demon_lord

    if request.method == 'POST':
        action = request.POST.get('action')
        ability_id = request.POST.get('ability_id')
        perform_turn(game_session, action, ability_id)

        if game_session.is_completed:
            return redirect(reverse('game_result', args=[game_id]))

    hero_abilities = []
    for char_ability in hero.abilities.all():
        cooldown_remaining = max(0, char_ability.ability.cooldown - (game_session.current_turn - char_ability.last_used_turn))
        can_use = cooldown_remaining == 0 and hero.mana >= char_ability.ability.mana_cost
        hero_abilities.append({
            'ability': char_ability.ability,
            'can_use': can_use,
            'cooldown_remaining': cooldown_remaining
        })

    actions = GameAction.objects.filter(game_session=game_session).order_by('-turn')[:5]

    context = {
        'game': game_session,
        'hero': hero,
        'demon_lord': demon_lord,
        'turn': game_session.current_turn,
        'hero_abilities': hero_abilities,
        'actions': actions,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('game/play.html', context, request=request)
        return JsonResponse({'html': html})
    else:
        return render(request, 'game/play.html', context)

def use_special_ability(character, ability, target, game_session):
    if character.mana >= ability.mana_cost:
        character.mana -= ability.mana_cost

        if ability.name == "Fireball":
            damage = 30 + character.attack // 2
            target.health = max(0, target.health - damage)
            result = f"{character.name}의 파이어볼! {target.name}에게 {damage}의 데미지!"
        elif ability.name == "Heal":
            heal = 40 + character.defense
            character.health = min(character.health + heal, character.max_health)
            result = f"{character.name}의 힐! {heal}만큼 체력 회복!"
        elif ability.name == "Curse":
            target.is_cursed = True
            target.curse_duration = 3
            target.accuracy *= 0.7
            target.evasion *= 0.7
            result = f"{character.name}의 저주! {target.name}의 명중률과 회피율이 30% 감소!"

        GameAction.objects.create(
            game_session=game_session,
            turn=game_session.current_turn,
            actor=character.__class__.__name__.upper(),
            action_type=ability.name.upper(),
            action_result='SUCCESS',
            description=result
        )

        if isinstance(character, Hero):
            ability_link = CharacterAbility.objects.get(hero=character, ability=ability)
        else:
            ability_link = CharacterAbility.objects.get(demon_lord=character, ability=ability)
        ability_link.last_used_turn = game_session.current_turn
        ability_link.save()

        character.save()
        if target != character:
            target.save()

        return result
    else:
        return f"{character.name}의 마나가 부족하여 {ability.name}을(를) 사용할 수 없습니다."

def end_game(game_session):
    game_session.is_completed = True
    if game_session.hero.health > game_session.demon_lord.health:
        game_session.winner = 'HERO'
    else:
        game_session.winner = 'DEMON'
    game_session.save()


@transaction.atomic
def perform_turn(game_session, hero_action, ability_id=None):
    print(f"Starting turn: {game_session.current_turn + 1}")
    hero = game_session.hero
    demon_lord = game_session.demon_lord

    game_session.current_turn += 1

    # Hero's turn
    if hero_action == 'attack':
        damage = max(0, hero.attack - demon_lord.defense)
        if random.random() < hero.accuracy:
            if random.random() >= demon_lord.evasion:
                demon_lord.health = max(0, demon_lord.health - damage)
                result = '공격했다!'
            else:
                result = '피했다!'
                damage = 0
        else:
            result = '빗나갔다!'
            damage = 0

        GameAction.objects.create(
            game_session=game_session,
            turn=game_session.current_turn,
            actor='HERO',
            action_type='ATTACK',
            action_result=result,
            damage_dealt=damage,
            description=f"영웅은 {result}/ 결과: {damage}만큼의 피해"
        )
        print(f"Hero action: Attack, Damage: {damage}, Result: {result}")
    elif hero_action == 'special':
        ability = SpecialAbility.objects.get(id=ability_id)
        result = use_special_ability(hero, ability, demon_lord, game_session)
        print(f"Hero action: Special Ability, Result: {result}")

    # Check game end condition after hero's turn
    if check_game_end(game_session, hero, demon_lord):
        return

    # Demon Lord's turn
    if demon_lord.health > 0:
        if random.random() < 0.3:  # 30% chance to use special ability
            abilities = SpecialAbility.objects.filter(characterability__demon_lord=demon_lord)
            if abilities.exists():
                ability = random.choice(abilities)
                result = use_special_ability(demon_lord, ability, hero, game_session)
                print(f"Demon Lord action: Special Ability, Result: {result}")
        else:
            damage = max(0, demon_lord.attack - hero.defense)
            if random.random() < demon_lord.accuracy:
                if random.random() >= hero.evasion:
                    hero.health = max(0, hero.health - damage)
                    result = '공격했다!'
                else:
                    result = '피했다!'
                    damage = 0
            else:
                result = '빗나갔다!'
                damage = 0

            GameAction.objects.create(
                game_session=game_session,
                turn=game_session.current_turn,
                actor='DEMON',
                action_type='ATTACK',
                action_result=result,
                damage_dealt=damage,
                description=f"마왕은 {result}/ 결과: {damage}만큼의 피해!"
            )
            print(f"Demon Lord action: Attack, Damage: {damage}, Result: {result}")

    # Check game end condition after demon lord's turn
    if check_game_end(game_session, hero, demon_lord):
        return

    # Handle curse effects
    handle_curse_effects(game_session, hero, demon_lord)

    hero.save()
    demon_lord.save()
    game_session.save()

    print(f"Turn {game_session.current_turn} completed")
    print(f"Hero HP: {hero.health}, Demon Lord HP: {demon_lord.health}")

def check_game_end(game_session, hero, demon_lord):
    if game_session.current_turn > 10 or hero.health <= 0 or demon_lord.health <= 0:
        end_game(game_session)
        return True
    return False

def handle_curse_effects(game_session, hero, demon_lord):
    for character in [hero, demon_lord]:
        if character.is_cursed:
            character.curse_duration -= 1
            if character.curse_duration <= 0:
                character.is_cursed = False
                character.accuracy /= 0.7
                character.evasion /= 0.7
                GameAction.objects.create(
                    game_session=game_session,
                    turn=game_session.current_turn,
                    actor='SYSTEM',
                    action_type='CURSE',
                    action_result='END',
                    description=f"{character.name}의 저주가 풀렸습니다!"
                )
                print(f"Curse ended for {character.name}")


@login_required
def game_result(request, game_id):
    game_session = GameSession.objects.get(id=game_id)
    context = {
        'game': game_session,
        'hero': game_session.hero,
        'demon_lord': game_session.demon_lord,
        'actions': GameAction.objects.filter(game_session=game_session).order_by('turn')
    }
    return render(request, 'game/result.html', context)