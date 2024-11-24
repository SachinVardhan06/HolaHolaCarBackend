# Generated by Django 5.1.3 on 2024-11-22 05:14

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_rename_note_ride_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='ride',
            name='contact_number',
            field=models.CharField(default=0, help_text='Contact number in the format +999999999. Up to 15 digits allowed.', max_length=10, validators=[django.core.validators.RegexValidator('^\\+?1?\\d{9,15}$', 'Enter a valid phone number.')]),
            preserve_default=False,
        ),
    ]