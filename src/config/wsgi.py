import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# One startup event per worker process, after Django configures the existing JSON logger.
import logging
from django.conf import settings
logging.getLogger("northstar.runtime").info("Application process started", extra={
    "fields": {"release": settings.RELEASE_ID, "environment": settings.ENVIRONMENT}})
