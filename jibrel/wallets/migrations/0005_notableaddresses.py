# Generated by Django 2.2.2 on 2020-01-24 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0004_wallet_deleted'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotableAddresses',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('address', models.CharField(max_length=42, unique=True)),
            ],
        ),
    ]
