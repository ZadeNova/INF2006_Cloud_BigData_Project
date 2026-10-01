# ---------- S3: one private bucket ----------
# Prefixes: data/ (dataset), exports/ (analytics). No CORS: the .glb models and product images are
# static files in the app image, served by WhiteNoise with hashed, cache-forever URLs, not from S3.
#
# Lab constraint (29 September 2026): the Learner Lab's service control policy denies
# s3:GetBucketObjectLockConfiguration, which the aws_s3_bucket resource calls on every read, so
# Terraform cannot manage the bucket itself. The bucket is created once with the CLI (command in
# evidence/aws-build-runbook.md, Procedures) and looked up here; every security setting on it below is
# still a Terraform resource. Teardown deletes the bucket with the CLI after `terraform destroy`.

data "aws_s3_bucket" "main" {
  bucket = var.s3_bucket_name
}

# Refuse every form of public access, whatever any later policy or ACL says.
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = data.aws_s3_bucket.main.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# ACLs off: access is decided only by IAM and the bucket policy.
resource "aws_s3_bucket_ownership_controls" "main" {
  bucket = data.aws_s3_bucket.main.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Keep previous versions, so an overwritten or deleted dataset file can be recovered.
resource "aws_s3_bucket_versioning" "main" {
  bucket = data.aws_s3_bucket.main.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption at rest with S3-managed keys (no customer-managed KMS key; see the plan's "Not built").
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = data.aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Cost control: old versions expire after 7 days; unfinished uploads are cleaned up after 1 day.
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = data.aws_s3_bucket.main.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Deny any request that is not over HTTPS. A data source only renders JSON; it creates nothing in IAM.
data "aws_iam_policy_document" "bucket_tls_only" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      data.aws_s3_bucket.main.arn,
      "${data.aws_s3_bucket.main.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "main" {
  bucket = data.aws_s3_bucket.main.id
  policy = data.aws_iam_policy_document.bucket_tls_only.json

  # S3 rejects simultaneous changes to one bucket's settings; apply the policy after public access is blocked.
  depends_on = [aws_s3_bucket_public_access_block.main]
}

# ---------- ECR: the app image registry ----------

resource "aws_ecr_repository" "app" {
  name                 = "${local.name_prefix}-app"
  image_tag_mutability = "IMMUTABLE" # a git-SHA tag always means the same image
  force_delete         = true        # lets `terraform destroy` remove it with images inside

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Images deployed are tagged release-<git-sha> (an extra tag on the same image; tags stay immutable) and
# terraform.tfvars points image_tag at it. ECR checks rules in priority order, and an image matching a
# higher-priority rule's tag filter cannot be expired by a lower one. So the deployed image and the 4
# releases before it (rollback targets) are never deleted by count or age.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the 5 newest releases"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["release-"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 3
        description  = "Delete non-release builds after 30 days"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = { type = "expire" }
      },
    ]
  })
}
