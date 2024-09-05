# Generated by Django 5.1 on 2024-09-05 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0010_alter_gamesession_is_completed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gamesession',
            name='result',
            field=models.CharField(choices=[('ongoing', 'Ongoing'), ('good_ending', 'Good Ending'), ('perfect_ending', 'Perfect Ending'), ('bad_ending', 'Bad Ending')], default='ongoing', max_length=20, null=True),
        ),
    ]
