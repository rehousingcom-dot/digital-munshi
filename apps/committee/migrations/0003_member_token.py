import uuid
from django.db import migrations, models


def gen_tokens(apps, schema_editor):
    M = apps.get_model("committee", "CommitteeMember")
    for m in M.objects.all():
        m.token = uuid.uuid4()
        m.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ('committee', '0002_committee_allow_join_committee_bidding_open_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='committeemember',
            name='token',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(gen_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='committeemember',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
