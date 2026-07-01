import uuid
from django.db import migrations, models


def gen_uuids(apps, schema_editor):
    Organization = apps.get_model("tenants", "Organization")
    for org in Organization.objects.all():
        org.catalog_uuid = uuid.uuid4()
        org.save(update_fields=["catalog_uuid"])


class Migration(migrations.Migration):
    dependencies = [("tenants", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="organization",
            name="catalog_uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="catalog_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(gen_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organization",
            name="catalog_uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
