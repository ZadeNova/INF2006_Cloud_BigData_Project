"""Helpers shared by the load harness: target allow-list, parsing of the shop's HTML, redaction, percentiles.

Standard library only, so analyze.py can import it without Locust installed.
"""
import ipaddress
import math
import re
from urllib.parse import urlsplit

HARNESS_VERSION = "1.0.0"

# The harness only ever talks to our own hosts (docs/plans/load-harness.md, section 1).
ALLOWED_REMOTE_HOSTS = {"shop-ec2.fourtytwofactors.me", "shop-fargate.fourtytwofactors.me"}
ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def check_base_url(url):
    """Return the normalised origin (scheme://host[:port]) or raise ValueError if the host is not ours."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host in ALLOWED_LOCAL_HOSTS:
        if parts.scheme not in ("http", "https"):
            raise ValueError(f"unsupported scheme in {url!r}")
    elif host in ALLOWED_REMOTE_HOSTS:
        if parts.scheme != "https":
            raise ValueError("remote targets must use https")
    else:
        raise ValueError(f"refusing target {host!r}: only {sorted(ALLOWED_REMOTE_HOSTS | ALLOWED_LOCAL_HOSTS)} are allowed")
    return f"{parts.scheme}://{parts.netloc}"


# --- parsing the shop's pages (regex is enough: the templates are ours and stable) -------------------------

_CSRF = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
_PRODUCT_LINK = re.compile(r'href="/products/(\d+)/"')
_OPTION = re.compile(r'<option value="(\d+)"([^>]*)>([^<]*)</option>')
_REVIEW = re.compile(r'name="review" value="([0-9a-f]{64})"')
_CART_LINE = re.compile(r"/cart/items/(\d+)/update/")
_CART_DELETE = re.compile(r"/cart/items/(\d+)/delete/")
_STATIC = re.compile(r'(?:href|src)="(/static/[^"#?]+\.(?:css|js|svg))(?:#[^"]*)?"')
_STOCK_TEXT = re.compile(r"Only \d+ of ")
_ORDER_PATH = re.compile(r"^/orders/(\d+)/$")


def csrf_token(html):
    m = _CSRF.search(html)
    return m.group(1) if m else None


def product_ids(html):
    """Distinct product ids linked from a catalogue page, in page order."""
    return list(dict.fromkeys(_PRODUCT_LINK.findall(html)))


def size_options(html):
    """(product_id, label, enabled) for each size in the add-to-cart select. The placeholder option has no id."""
    return [(v, label.strip(), "disabled" not in attrs) for v, attrs, label in _OPTION.findall(html)]


def pick_size(options, rng):
    """A random enabled size, preferring ones not flagged 'only N left' (stock above the low-stock threshold)."""
    enabled = [o for o in options if o[2]]
    roomy = [o for o in enabled if "only" not in o[1] and "sold out" not in o[1]]
    pool = roomy or enabled
    return rng.choice(pool)[0] if pool else None


def review_value(html):
    m = _REVIEW.search(html)
    return m.group(1) if m else None


def cart_line_ids(html):
    return list(dict.fromkeys(_CART_LINE.findall(html)))


def cart_delete_ids(html):
    return list(dict.fromkeys(_CART_DELETE.findall(html)))


def static_assets(html):
    """Same-origin CSS, JS and SVG sprites a cold browser would fetch. 3D models (.glb) are deliberately excluded (D1)."""
    return list(dict.fromkeys(_STATIC.findall(html)))


def is_stock_message(html):
    """True for the app's stock refusals: 'Only N of "X" in stock (indicative).' and '... left in stock.'"""
    return bool(_STOCK_TEXT.search(html))


def order_id_from_location(location):
    path = urlsplit(location or "").path
    m = _ORDER_PATH.match(path)
    return m.group(1) if m else None


# --- redaction: nothing reaches evidence/raw without passing through this -----------------------------------

_ACCOUNT_ID = re.compile(r"(?<!\d)\d{12}(?!\d)")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def _redact_ip(match):
    try:
        ip = ipaddress.ip_address(match.group(0))
    except ValueError:
        return match.group(0)
    return match.group(0) if (ip.is_private or ip.is_loopback or ip.is_link_local) else "<PUBLIC-IP>"


def redact(text):
    """12-digit AWS account ids become <ACCOUNT>; public IPv4 addresses become <PUBLIC-IP>. Private addresses stay."""
    return _IPV4.sub(_redact_ip, _ACCOUNT_ID.sub("<ACCOUNT>", text))


# --- statistics ---------------------------------------------------------------------------------------------

def percentile(values, p):
    """Nearest-rank percentile of an unsorted list; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def median(values):
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


# --- prices (prices.json) -----------------------------------------------------------------------------------

def unit_hour(prices, variant):
    """Hourly cost of one unit of compute: a c5.large instance (A) or a Fargate task of the configured size (B)."""
    if variant == "ec2":
        return prices["ec2_c5_large_hour"]
    task = prices["fargate_task"]
    return task["vcpu"] * prices["fargate_vcpu_hour"] + task["gb"] * prices["fargate_gb_hour"]


def fixed_hour(prices):
    """Hourly cost that does not depend on the number of units: the ALB and its two public IPv4 addresses."""
    return prices["alb_hour"] + 2 * prices["public_ipv4_hour"]
