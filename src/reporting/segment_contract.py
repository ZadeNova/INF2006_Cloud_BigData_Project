"""Standard-library-only contract shared by the offline producer and Django loader."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from uuid import UUID


FORMAT = "rfm-batch-v1"
FEATURE_SCHEMA = "lifetime-completed-rfm-v1"


def digest(value):
    """Canonical JSON SHA-256; normalize equivalent float/Decimal JSON numbers."""
    def normalize(item):
        if isinstance(item, dict):
            return {key: normalize(val) for key, val in item.items()}
        if isinstance(item, list):
            return [normalize(val) for val in item]
        if isinstance(item, (float, Decimal)):
            number = Decimal(str(item))
            return int(number) if number == number.to_integral_value() else float(number)
        return item
    encoded = json.dumps(normalize(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def model_version(training):
    return "rfm-v3-" + digest(training)


def batch_id(payload):
    return digest({key: value for key, value in payload.items()
                   if key not in {"batch_id", "generated_at"}})


def source_binding(connection):
    # A deployment/database association configured independently at each endpoint.
    # This is deliberately not derived from a namespace or a database credential.
    source_id = str(UUID(os.environ.get("ML_SOURCE_ID", "")))
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        database = cursor.fetchone()[0]
    return {"source_id": source_id, "database": database}


def run_binding(run):
    return {"run_id": str(run["run_id"]), "namespace": run["namespace"],
            "cutoff": run["cutoff"].astimezone(timezone.utc).isoformat(),
            "inventory_version": run["inventory_version"],
            "summary_version": str(run["summary_version"])}


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError
    return value


def decimal_value(value, minimum, maximum, places):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError
    result = Decimal(str(value))
    if not result.is_finite() or not minimum <= result <= maximum:
        raise ValueError
    if result != result.quantize(Decimal(1).scaleb(-places)):
        raise ValueError
    return result


def text_value(value, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError
    value.encode("utf-8")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def validate_rows(payload, expected_run, expected_model=None):
    """Validate once, returning normalized dictionaries suitable for model creation."""
    try:
        file_run = UUID(payload["run_id"])
        expected_run = UUID(str(expected_run))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise ValueError("Explicit valid run_id values are required") from None
    if file_run != expected_run:
        raise ValueError("JSON run_id does not match --run-id")
    try:
        version = text_value(payload["model_version"], 100)
        if expected_model is not None and expected_model != version:
            raise ValueError
        k = integer(payload["k_clusters"], 2, 32767)
        score = payload["silhouette_score"]
        score = None if score is None else decimal_value(score, -1, 1, 4)
    except (KeyError, ValueError, TypeError, InvalidOperation, UnicodeError):
        raise ValueError("Invalid or missing model metadata") from None
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("rows must be a non-empty JSON array")
    assignments = []
    for index, item in enumerate(rows, 1):
        try:
            if not isinstance(item, dict):
                raise ValueError
            row = dict(
                customer_id=integer(item["customer_id"], 1, 2147483647),
                cluster_id=integer(item["cluster_id"], 0, k - 1),
                segment_label=text_value(item["segment_label"], 40),
                recency_days=integer(item["recency_days"], 0, 2147483647),
                frequency_orders=integer(item["frequency_orders"], 1, 2147483647),
                monetary_total=decimal_value(item["monetary_total"], 0, Decimal("9999999999999999.99"), 2),
                k_clusters=integer(item["k_clusters"], 2, 32767),
                silhouette_score=(None if item["silhouette_score"] is None
                                  else decimal_value(item["silhouette_score"], -1, 1, 4)),
            )
            if row["k_clusters"] != k or row["silhouette_score"] != score:
                raise ValueError
        except (KeyError, ValueError, TypeError, InvalidOperation, UnicodeError):
            raise ValueError(f"rows[{index}] has invalid or inconsistent fields") from None
        assignments.append(row)
    if len({row["customer_id"] for row in assignments}) != len(assignments):
        raise ValueError("Duplicate customer assignments")
    labels = {}
    for row in assignments:
        if row["cluster_id"] in labels and labels[row["cluster_id"]] != row["segment_label"]:
            raise ValueError("Each cluster must have one consistent segment label")
        labels[row["cluster_id"]] = row["segment_label"]
    return assignments


def validate_batch(payload, expected_run, expected_source):
    """Check completed export integrity and its independently selected destination."""
    try:
        if payload["format"] != FORMAT or payload["status"] != "completed":
            raise ValueError
        if payload["run"] != run_binding(expected_run) or payload["source"] != expected_source:
            raise ValueError
        if payload["run_id"] != payload["run"]["run_id"]:
            raise ValueError
        generated = datetime.fromisoformat(payload["generated_at"])
        if generated.tzinfo is None:
            raise ValueError
        training = payload["training"]
        if training["feature_schema"] != FEATURE_SCHEMA or training["algorithm"] != "sklearn-kmeans":
            raise ValueError
        if training["preprocessing"] not in {"baseline", "log_frequency", "log_rfm_aov"}:
            raise ValueError
        if training["selection"] != "highest-valid-silhouette-smaller-k-tie" or training["n_init"] != "auto":
            raise ValueError
        low = integer(training["min_k"], 2, 4)
        high = integer(training["max_k"], low, 4)
        integer(payload["k_clusters"], low, high)
        integer(training["seed"], 0, 4294967295)
        if training["stability_seeds"] != [42, 99, 123, 777] or training["silhouette_sample_limit"] != 5000:
            raise ValueError
        provenance = training["provenance"]
        text_value(provenance["python"], 100)
        for package in ("numpy", "pandas", "scikit-learn", "scipy", "psycopg", "joblib", "threadpoolctl"):
            text_value(provenance["dependencies"][package], 100)
        for path in ("analytics/segment_customers.py", "analytics/requirements.txt", "src/reporting/segment_contract.py"):
            value = provenance["code_sha256"][path]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError
        if payload["model_version"] != model_version(training) or payload["batch_id"] != batch_id(payload):
            raise ValueError
    except (KeyError, ValueError, TypeError, AttributeError, InvalidOperation, UnicodeError, OverflowError):
        raise ValueError("Invalid completed batch, provenance or destination; regenerate the export") from None
