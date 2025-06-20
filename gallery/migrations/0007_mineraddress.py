# Generated by Django 5.2.2 on 2025-06-09 09:11

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0006_userprofile_imagecomment_imageupvote'),
    ]

    operations = [
        migrations.CreateModel(
            name='MinerAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wallet_address', models.CharField(db_index=True, help_text='Ethereum wallet address of the miner', max_length=42, unique=True)),
                ('first_seen', models.DateTimeField(default=django.utils.timezone.now, help_text='When this miner was first identified')),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now, help_text='When this miner was last seen submitting solutions/commitments')),
                ('total_solutions', models.PositiveIntegerField(default=0, help_text='Total number of solutions submitted by this miner')),
                ('total_commitments', models.PositiveIntegerField(default=0, help_text='Total number of commitments submitted by this miner')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this miner is currently considered active')),
            ],
            options={
                'ordering': ['-last_seen'],
                'indexes': [models.Index(fields=['wallet_address'], name='gallery_min_wallet__0ee143_idx'), models.Index(fields=['last_seen'], name='gallery_min_last_se_7c5922_idx'), models.Index(fields=['is_active'], name='gallery_min_is_acti_6e3ed7_idx')],
            },
        ),
    ]
