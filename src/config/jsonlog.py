"""JSON log formatter with a deliberately small, safe field list (docs/SECURITY.md; review finding SEC-001).

One JSON object per line on standard output, which container runtimes and CloudWatch Logs both collect.
Exceptions are reduced to their class name and a short list of stack frames (file, line, function). The
exception message, the source lines, local variables, request bodies, cookies and headers are never
included, because messages routinely echo user input or database detail (for example a duplicate key value).
"""
import json
import logging
import os
import traceback
from datetime import datetime, timezone

FRAME_LIMIT = 8


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "fields", None) or {})
        request = getattr(record, "request", None)     # Django attaches the request to its error records
        if request is not None and "request_id" not in payload:
            payload["request_id"] = getattr(request, "request_id", None)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = record.exc_info[0].__name__
            payload["frames"] = _frames(record.exc_info[2])
        return json.dumps(payload, default=str, separators=(",", ":"))


def _frames(tb):
    """The innermost frames as 'dir/file.py:line function', with paths cut to their last two components."""
    frames = []
    for frame in traceback.extract_tb(tb)[-FRAME_LIMIT:]:
        short = os.path.join(*frame.filename.replace("\\", "/").split("/")[-2:])
        frames.append(f"{short}:{frame.lineno} {frame.name}")
    return frames
