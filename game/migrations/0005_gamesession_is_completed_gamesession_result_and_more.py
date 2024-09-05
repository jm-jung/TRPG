# Generated by Django 5.1 on 2024-09-04 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0004_remove_characterability_ability_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamesession',
            name='is_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='gamesession',
            name='result',
            field=models.CharField(choices=[('ongoing', 'Ongoing'), ('good_ending', 'Good Ending'), ('perfect_ending', 'Perfect Ending'), ('bad_ending', 'Bad Ending')], default='ongoing', max_length=20),
        ),
        migrations.AddField(
            model_name='storyprogress',
            name='next_chapter_threshold',
            field=models.IntegerField(default=20),
        ),
        migrations.AddField(
            model_name='storyprogress',
            name='story_path',
            field=models.CharField(default='', max_length=1),
        ),
        migrations.AlterField(
            model_name='storyprogress',
            name='plot_points',
            field=models.JSONField(default=list),
        ),
    ]
