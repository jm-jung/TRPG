from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username

class GameSession(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(default='ongoing',max_length=20, choices=[
        ('ongoing', 'Ongoing'),
        ('victory', 'Victory'),
        ('defeat', 'Defeat')
    ])
    result = models.CharField( max_length=20, choices=[
        ('ongoing', 'Ongoing'),
        ('good_ending', 'Good Ending'),
        ('perfect_ending', 'Perfect Ending'),
        ('bad_ending', 'Bad Ending')
    ], default='ongoing')

    def __str__(self):
        return f"Game Session for {self.player.username}"

class Dialogue(models.Model):
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name='dialogues')
    timestamp = models.DateTimeField(auto_now_add=True)
    speaker = models.CharField(max_length=10, choices=[('player', 'Player'), ('demon_lord', 'Demon Lord')])
    content = models.TextField()

class StoryProgress(models.Model):
    game_session = models.OneToOneField(GameSession, on_delete=models.CASCADE)
    current_chapter = models.IntegerField(default=1)
    progress = models.IntegerField(default=0)  # 'chapter_progress'를 'progress'로 변경
    plot_points = models.JSONField(default=list)
    def __str__(self):
        return f"Story Progress for Game Session {self.game_session.id}"

class GameState(models.Model):
    game_session = models.OneToOneField(GameSession, on_delete=models.CASCADE)
    player_persuasion_level = models.IntegerField(default=0)  # 플레이어의 설득력 수준
    demon_lord_resistance = models.IntegerField(default=100)  # 마왕의 저항력
    player_emotional_state = models.CharField(max_length=50, default='neutral')  # 플레이어의 감정 상태
    demon_lord_emotional_state = models.CharField(max_length=50, default='hostile')  # 마왕의 감정 상태
    argument_strength = models.IntegerField(default=0)  # 현재 논점의 강도
    environmental_factors = models.JSONField(default=dict)  # 예: 대화 장소, 시간 등

class GameResult(models.Model):
    game_session = models.OneToOneField(GameSession, on_delete=models.CASCADE, related_name='game_result')
    result = models.CharField(max_length=50)
    end_time = models.DateTimeField(auto_now_add=True)
    final_persuasion_level = models.FloatField()
    final_demon_resistance = models.FloatField()
    final_chapter = models.IntegerField()
    total_turns = models.IntegerField()
    duration = models.DurationField()
    def __str__(self):
        return f"Game Result for Session {self.game_session.id} - {self.result}"