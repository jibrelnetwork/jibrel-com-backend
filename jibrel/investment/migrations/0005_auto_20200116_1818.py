# Generated by Django 2.2.2 on 2020-01-16 18:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0004_auto_20200115_1657'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investmentapplication',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applications', to=settings.DJANGO_BANKING_USER_MODEL),
        ),
    ]
