# Generated by Django 2.2.2 on 2019-12-24 14:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_auto_20191223_1143'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='is_agreed_privacy_policy',
            new_name='is_agreed_documents',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='is_agreed_terms',
        ),
    ]
