from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_add_website_scrape"),
    ]

    operations = [
        migrations.AddField(
            model_name="websitescrape",
            name="posts",
            field=models.JSONField(blank=True, default=list),
        ),
    ]



