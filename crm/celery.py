import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

app = Celery("crm")

# Load config from Django settings, use `CELERY_` prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in apps
app.autodiscover_tasks()
