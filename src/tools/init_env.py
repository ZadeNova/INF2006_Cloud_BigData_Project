"""Create local configuration once, without printing secrets or replacing existing state."""
import os
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / ".env"
text = (path.parent / ".env.example").read_text()
text = text.replace("replace-django-secret", secrets.token_urlsafe(64))
text = text.replace("replace-database-password", secrets.token_urlsafe(32))
text = text.replace("replace-admin-password", secrets.token_urlsafe(32))
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Existing .env preserved.")
else:
    with os.fdopen(fd, "w") as output:
        output.write(text)
    print("Created local .env; secrets were not printed.")
