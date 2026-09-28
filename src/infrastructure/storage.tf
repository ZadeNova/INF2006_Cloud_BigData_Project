# ---------- S3: one private bucket ----------
# Prefixes: data/ (dataset), exports/ (analytics), media/images/, media/models/ (.glb).
#
# Lab constraint (29 September 2026): the Learner Lab's service control policy denies
# s3:GetBucketObjectLockConfiguration, which the aws_s3_bucket resource calls on every read, so
# Terraform cannot manage the bucket itself. The bucket is created once with the CLI (command in
# docs/plans/aws-terraform-stage-1.md) and looked up here; every security setting on it below is
# still a Terraform resource. Teardown deletes the bucket with the CLI after `terraform destroy`.

data "aws_s3_bucket" "main" {
  bucket = var.s3_bucket_name
}

# The first apply created the bucket as a resource before the read failed. Forget that resource
# without deleting the bucket, which is kept and looked up above.
removed {
  from = aws_s3_bucket.main

  lifecycle {
    destroy = false
  }
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

# The 3D viewer fetches .glb models from JavaScript, which needs CORS; <img> tags do not.
# Only the shop's own HTTPS origin, read-only. Created once var.app_hostname is set.
resource "aws_s3_bucket_cors_configuration" "main" {
  count  = var.app_hostname == null ? 0 : 1
  bucket = data.aws_s3_bucket.main.id

  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["https://${var.app_hostname}"]
    allowed_headers = ["*"]
    max_age_seconds = 3600
  }
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

# Keep the 10 newest images; older ones are deleted automatically.
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
