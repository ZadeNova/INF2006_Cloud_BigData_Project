from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("reporting", "0003_completed_sale_lines_view")]

    operations = [
        migrations.AlterModelOptions(
            name="analyticsrun",
            options={"permissions": [("view_analytics", "Can view sales and inventory analytics")]},
        ),
    ]
