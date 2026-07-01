from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("party", "0004_party_share_uuid")]
    operations = [
        migrations.AddField(
            model_name="party",
            name="loyalty_points",
            field=models.IntegerField(default=0),
        ),
    ]
