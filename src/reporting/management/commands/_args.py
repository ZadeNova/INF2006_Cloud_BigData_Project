"""Shared argument helpers (underscore-prefixed, so Django does not treat this as a command)."""
import argparse
from datetime import date


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a YYYY-MM-DD date") from None
