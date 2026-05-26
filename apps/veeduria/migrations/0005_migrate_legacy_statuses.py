"""Map legacy Complaint.status values to the new operational pipeline.

- ``under_review`` → ``triaged`` (the previous catch-all "in progress")
- ``closed``       → ``resolved`` (the previous terminal state)

Reverse mapping is provided for completeness, although new statuses without
a legacy equivalent (in_field, escalated, rejected) collapse onto
``under_review`` to remain within the old constraint.
"""

from django.db import migrations

FORWARD = {
    'under_review': 'triaged',
    'closed': 'resolved',
}

REVERSE = {
    'triaged': 'under_review',
    'in_field': 'under_review',
    'escalated': 'under_review',
    'resolved': 'closed',
    'rejected': 'closed',
}


def forward(apps, schema_editor):
    Complaint = apps.get_model('veeduria', 'Complaint')
    for old, new in FORWARD.items():
        Complaint.objects.filter(status=old).update(status=new)


def reverse(apps, schema_editor):
    Complaint = apps.get_model('veeduria', 'Complaint')
    for new, old in REVERSE.items():
        Complaint.objects.filter(status=new).update(status=old)


class Migration(migrations.Migration):

    dependencies = [
        ('veeduria', '0004_extend_complaint_and_status_event'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
