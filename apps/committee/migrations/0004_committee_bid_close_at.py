from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('committee', '0003_member_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='committee',
            name='bid_close_at',
            field=models.DateTimeField(blank=True, null=True,
                                       help_text='Is time ke baad boli nahi lag sakti (deadline)'),
        ),
    ]
