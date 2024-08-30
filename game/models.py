from django.db import models
from django.contrib.auth.models import User


class Character(models.Model):
    name = models.CharField(max_length=100)
    health = models.IntegerField(default=100)
    max_health = models.IntegerField(default=100)
    attack = models.IntegerField(default=10)
    defense = models.IntegerField(default=5)
    accuracy = models.FloatField(default=0.8)
    evasion = models.FloatField(default=0.2)
    mana = models.IntegerField(default=100)
    max_mana = models.IntegerField(default=100)
    is_cursed = models.BooleanField(default=False)
    curse_duration = models.IntegerField(default=0)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Hero(Character):
    player = models.ForeignKey(User, on_delete=models.CASCADE)


class DemonLord(Character):
    pass


class SpecialAbility(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    cooldown = models.IntegerField(default=3)
    mana_cost = models.IntegerField(default=20)

    def __str__(self):
        return self.name


class CharacterAbility(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='abilities', null=True, blank=True)
    demon_lord = models.ForeignKey(DemonLord, on_delete=models.CASCADE, related_name='abilities', null=True, blank=True)
    ability = models.ForeignKey(SpecialAbility, on_delete=models.CASCADE)
    last_used_turn = models.IntegerField(default=0)

    def __str__(self):
        if self.hero:
            return f"{self.hero.name}'s {self.ability.name}"
        else:
            return f"{self.demon_lord.name}'s {self.ability.name}"


class GameSession(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE)
    demon_lord = models.ForeignKey(DemonLord, on_delete=models.CASCADE)
    current_turn = models.IntegerField(default=0)  # 0으로 변경
    max_turns = models.IntegerField(default=10)  # 새로운 필드 추가
    is_completed = models.BooleanField(default=False)
    winner = models.CharField(max_length=10, choices=[('HERO', 'Hero'), ('DEMON', 'Demon Lord')], null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_turns = models.IntegerField(default=10)
    def __str__(self):
        return f"Game {self.id}: {self.player.username} vs {self.demon_lord.name}"

    def increment_turn(self):
        self.current_turn += 1
        self.save()

    def is_game_over(self):
        return self.current_turn >= self.max_turns or self.is_completed

class GameAction(models.Model):
    ACTION_TYPES = (
        ('ATTACK', 'Attack'),
        ('DEFEND', 'Defend'),
        ('SPECIAL', 'Special Move'),
        ('CURSE', 'Curse'),
    )

    ACTION_RESULTS = (
        ('HIT', 'Hit'),
        ('MISS', 'Miss'),
        ('EVADE', 'Evaded'),
        ('CRITICAL', 'Critical Hit'),
    )

    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='actions')
    turn = models.IntegerField()
    actor = models.CharField(max_length=10, choices=[('HERO', 'Hero'), ('DEMON', 'Demon Lord')])
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    action_result = models.CharField(max_length=10, choices=ACTION_RESULTS)
    damage_dealt = models.IntegerField(default=0)
    description = models.TextField()

    def __str__(self):
        return f"Turn {self.turn}: {self.actor} {self.action_type} - {self.action_result}"