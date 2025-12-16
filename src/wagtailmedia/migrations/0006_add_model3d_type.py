from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailmedia", "0005_alter_media_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="media",
            name="type",
            field=models.CharField(
                choices=[
                    ("audio", "Audio file"),
                    ("video", "Video file"),
                    ("model3d", "3D model"),
                ],
                max_length=255,
            ),
        ),
    ]
