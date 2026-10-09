"""Fargate job: import the shoe dataset (scripts/jobs.sh fargate import).

Runs inside the unchanged app image as `python -c "<this file>"`. The image has no data folder, so the dataset comes from
the bucket (jobs.sh uploaded it there, after checking it against checksums.txt), then the app's own create-only
import_dataset command loads it. Settings arrive as JOB_* environment variables; none of them is a secret.
"""
import os
from pathlib import Path

import boto3

bucket, namespace = os.environ["JOB_BUCKET"], os.environ["JOB_NAMESPACE"]
prefix, target = os.environ.get("JOB_PREFIX", "data/derived/shoes/"), Path("/tmp/shoes")

s3 = boto3.client("s3", region_name=os.environ.get("JOB_REGION", "us-east-1"))
count = 0
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
    for item in page.get("Contents", []):
        name = item["Key"][len(prefix):]
        if not name or name.endswith("/"):
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, item["Key"], str(destination))
        count += 1
if count == 0:
    raise SystemExit(f"no dataset files under s3://{bucket}/{prefix}")
print(f"Downloaded {count} dataset files.", flush=True)
os.execvp("python", ["python", "manage.py", "import_dataset", "--source", str(target), "--namespace", namespace])
