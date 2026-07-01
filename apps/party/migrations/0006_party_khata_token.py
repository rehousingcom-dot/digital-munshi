import uuid
from django.db import migrations, models


def gen_tokens(apps, schema_editor):
    P = apps.get_model("party", "Party")
    for p in P.objects.all():
        p.khata_token = uuid.uuid4()
        p.save(update_fields=["khata_token"])


class Migration(migrations.Migration):

    dependencies = [
        ('party', '0005_party_loyalty_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='party',
            name='khata_token',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gen_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='party',
            name='khata_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
