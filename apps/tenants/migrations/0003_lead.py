from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tenants", "0002_org_catalog")]
    operations = [
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=20)),
                ("business", models.CharField(blank=True, max_length=160)),
                ("message", models.TextField(blank=True)),
                ("source", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
