from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_bookmark_category_notification_postimage_tag_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
    ]

