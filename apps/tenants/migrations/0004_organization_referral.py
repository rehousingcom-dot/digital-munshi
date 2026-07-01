from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_lead'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='referral_code',
            field=models.CharField(blank=True, max_length=16, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='referred_by',
            field=models.ForeignKey(blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='referrals', to='tenants.organization'),
        ),
    ]
