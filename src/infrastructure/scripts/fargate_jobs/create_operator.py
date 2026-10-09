"""Fargate job: create the demo-operator login (scripts/jobs.sh fargate operator).

Runs inside the unchanged app image as `python -c "<this file>"`. The password is generated here, handed to the app's
seed_demo command through the environment of that one process, and stored in the operator secret with boto3. It is
never printed and never passes through a command line or a Terraform file. Skips if the operator secret already holds
a value, so a rerun never replaces a password the database does not have.
"""
import json
import os
import secrets
import subprocess
import sys

import boto3

secret_id = os.environ.get("JOB_OPERATOR_SECRET", "inf2006-grp21/operator")
client = boto3.client("secretsmanager", region_name=os.environ.get("JOB_REGION", "us-east-1"))

try:
    client.get_secret_value(SecretId=secret_id)
except client.exceptions.ResourceNotFoundException:
    pass   # the secret exists but holds no value yet (a new secret, or a failed earlier run): create the login
else:
    print("operator secret already set; leaving the operator account as it is")
    sys.exit(0)

password = secrets.token_urlsafe(18)
subprocess.run(["python", "manage.py", "seed_demo", "--no-products"],
               env={**os.environ, "DEMO_OPERATOR_PASSWORD": password}, check=True)
client.put_secret_value(SecretId=secret_id, SecretString=json.dumps({"username": "demo-operator", "password": password}))
print("demo-operator created; the password is in the operator secret")
