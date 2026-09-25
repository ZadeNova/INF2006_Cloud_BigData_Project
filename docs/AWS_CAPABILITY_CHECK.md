# How to use the AWS capability check

The capability check is a small script, `src/tools/aws_capability_check.py`, that records read API and EC2 dry-run outcomes from your AWS lab account and writes the answer as a Markdown file. It is item B4 in [cloud-independent-prep.md](plans/cloud-independent-prep.md). Run it **once, before the Terraform build**, to identify deployment blockers. ECR and Secrets Manager are already selected; listing them does not prove push/pull or secret retrieval permission.

**It is safe.** It only lists and describes things. For "could I create a VPC?" and "could I launch an instance?" it uses the AWS `--dry-run` option, which asks AWS whether the call *would* work and creates nothing. It provisions no resources; check current API pricing and lab limits when running it. A test (`test_no_probe_can_change_anything`) fails if anyone adds a call that could create, change or delete something.

**It does not tell you:** your remaining balance (read it from the lab page), the price of anything, or whether you can *create* an ALB, Auto Scaling group, RDS database, S3 bucket, IAM role or certificate. A Terraform plan does not prove creation permission either. Verify the authorised Terraform apply and actual deployed behaviour.

## What you need

- A computer with **Python 3** (`python3 --version`).
- The **AWS CLI version 2** (`aws --version`). Install steps are below.
- Your **lab running**, so you have credentials.
- This repository checked out, with commands run **from the repository root**.

## Step 1: Install the AWS CLI (once)

Check first: `aws --version`. If it prints `aws-cli/2.x`, skip to step 2.

**Linux (x86_64):**

```bash
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

**Windows:** run `msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi` (or download the installer from AWS), then open a new terminal and run `aws --version`.

**macOS:** `curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o AWSCLIV2.pkg && sudo installer -pkg AWSCLIV2.pkg -target /`.

## Step 2: Start the lab and copy its credentials

The steps below are for AWS Academy's Learner Lab; if your lab is different, its start page has an equivalent "CLI credentials" button.

1. Open the lab and press **Start Lab**. Wait until the status light beside "AWS" turns **green**.
2. Note the **region** shown in the lab or in the AWS console (top right). Learner Labs usually use `us-east-1`. You will pass this in step 4.
3. Note the **remaining balance** shown on the lab page. Write it down; the tool cannot read it.
4. Press **AWS Details**, then next to "AWS CLI" press **Show**. You will see a block like this (values shortened):

   ```text
   [default]
   aws_access_key_id=ASIA...
   aws_secret_access_key=...
   aws_session_token=...
   ```

## Step 3: Give the credentials to the AWS CLI

Choose **one** way. Both keep the credentials **outside the repository**, and you must **never commit, paste into chat, or screenshot them**.

**Option A: the credentials file (recommended, nothing to type each time):**

```bash
mkdir -p ~/.aws
nano ~/.aws/credentials        # paste the whole block from step 2, save
chmod 600 ~/.aws/credentials
```

**Option B: environment variables (this terminal only):**

```bash
export AWS_ACCESS_KEY_ID='ASIA...'
export AWS_SECRET_ACCESS_KEY='...'
export AWS_SESSION_TOKEN='...'
```

Check that it works:

```bash
aws sts get-caller-identity --region us-east-1
```

You should see an `Account` and an `Arn`. That output names your session, so **do not share it**. If you see an error instead, go to "If something goes wrong" below.

Lab credentials **expire after a few hours** (the lab page shows a countdown). When they do, start the lab again and repeat steps 2 and 3.

## Step 4: Run the check

First a **dry read on screen**, writing no file:

```bash
python3 src/tools/aws_capability_check.py --region us-east-1
```

It takes about a minute and prints a table. When you are happy with it, write the record:

```bash
python3 src/tools/aws_capability_check.py --region us-east-1 --output evidence/aws-capability-record.md
```

Replace `us-east-1` with your lab's region. If you use a named AWS profile, add `--profile <name>`.

## Step 5: Read the result

Each row of the table has one of four results:

| Result | Meaning |
|---|---|
| **allowed** | The call worked (or the dry run said it would have). |
| **denied** | The lab's policy refused it. This is information, not a failure of the tool. |
| **error** | Something else happened. Read the Detail column. A row saying "Timed out after 45 seconds" means AWS was slow; rerun the check. |
| **skipped** | The check needs an earlier one that did not succeed (for example the instance dry run needs the AMI lookup). |

What each area tells you, and the decision it feeds:

| Area | Look for | Decision |
|---|---|---|
| Identity | account and principal shown | Confirms you are in the intended account. Only the last 4 digits and the role are printed. |
| Network | 2 or more availability zones; create a VPC (dry run) allowed | Zone discovery and the specific VPC dry run only; subnet/routing and deployment still need verification. |
| Compute | instance types offered, launch dry run allowed, vCPU quota | Which instance size to use, and the maximum of 2 in the Auto Scaling group. |
| Load balancing, Scaling | ALB and Auto Scaling lists allowed | Whether the ALB and Auto Scaling group are reachable. |
| Database | RDS list allowed; default PostgreSQL engine version | The engine version to choose for RDS. |
| Storage | S3 list allowed | Bucket discovery only; creation and object access still need verification. |
| IAM | instance profiles and roles: allowed, and their names | Record the EC2 instance profile. Scheduler/Lambda roles are not required by the selected batch ML workflow. Verify trust/resource policies and deployer iam:PassRole; list access proves none of these. Reference permitted lab roles where required. |
| Secrets | Secrets Manager allowed or denied | Secrets Manager is selected for database credentials/shared `DJANGO_SECRET_KEY`. Unavailable storage/retrieval blocks deployment; never use plaintext user data or launch-template secrets. Verify retrieval through least-privilege runtime roles. |
| HTTPS | ACM and Route 53 allowed or denied | Listing does not prove issuance/import permission or hostname ownership. Test option B needs permitted import, a matching hostname and explicit client trust; it is not guaranteed. See B4 in [cloud-independent-prep.md](plans/cloud-independent-prep.md). |
| Registry | ECR allowed or denied | ECR is selected. Separately verify creation, push and instance pull access; resolve denied access before deployment. |
| Audit, Protection | CloudTrail trails and regional WAF web ACLs | Discovery only; verify audit events and ALB rule enforcement after deployment. |
| Scheduling, Inference | Scheduler schedules and Lambda functions | Legacy discovery only; these services are no longer selected. Probe availability is not a deployment requirement; ML uses an explicitly triggered batch workflow. |
| Monitoring, Cost | CloudWatch, SNS, Budgets allowed | Discovery only; verify alarm delivery, SNS notification and cost controls separately. |

Systems Manager is not selected; the AMI lookup uses EC2 image discovery. Agree a secure administration method with the infrastructure owner. The generated record includes role checks to complete manually; it does not inspect trust policies or simulate role permissions. No secret values are retrieved.

## Step 6: Add the balance and review the file before committing

1. Open `evidence/aws-capability-record.md`. Near the end is a line `USD ____ on ____`. Fill in the balance from the lab page and today's date.
2. The record goes into the graded submission, and the brief forbids personal data and account details in evidence. The tool masks account numbers, session names, IAM user names and email addresses, but **check it yourself**:

   ```bash
   grep -nE "[0-9]{9,}|@" evidence/aws-capability-record.md
   ```

   The command should print **nothing** (no long numbers, no email addresses). Then read the **Detail** column once by eye. Denied calls quote the caller and often show text like `arn:aws:sts::<account>:assumed-role/voclabs/<session>`; that is correct and expected, because the account number and session name were replaced. What you are looking for is anything that looks like a real name, student ID or number where `<account>` or `<session>` should be. If you find something, delete it from the file (and tell the team so the masking can be improved).
3. Only then commit the file. Do not commit anything from `~/.aws/`.

## If something goes wrong

| You see | Cause and fix |
|---|---|
| `The AWS CLI (aws) is not installed or not on PATH.` | Do step 1, then open a new terminal. |
| `No AWS credentials found.` | Do step 3. If you used option B, run the `export` lines in the **same** terminal. |
| `The AWS session token has expired.` | Start the lab again, copy fresh credentials (step 2), update them (step 3) and rerun. |
| Every row is `denied`, or `Could not connect to the endpoint URL` | The lab is not running, the credentials are stale, or the region is wrong. Check the light on the lab page and the region name. |
| A row says `Timed out after 45 seconds` | AWS was slow for that call. Rerun; the other rows are not lost. |
| `python3: can't open file` | You are not in the repository root. `cd` there first. |

## Checking the tool itself

The tool has its own tests, which use a fake AWS CLI and contact nothing:

```bash
docker compose build web
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests/test_aws_capability_check.py
```

## What to do with the result

Share the record with the group. It supplies the gates for the Terraform build ([aws-terraform.md](plans/aws-terraform.md)): the capability record, the HTTPS answer, the balance and cap, and the image route. Keep it under `evidence/` so the report can cite it, after replacing lab-generated role names (long random-looking prefixes) with `<lab-generated>`. The Terraform apply then proves what the probe could only list. The first run, on 25 September 2026, is summarised under B4 in [cloud-independent-prep.md](plans/cloud-independent-prep.md).
