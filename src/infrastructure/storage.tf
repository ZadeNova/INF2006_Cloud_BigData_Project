# ---------- S3: one private bucket ----------
# Prefixes: data/ (dataset), exports/ (analytics), media/images/, media/models/ (.glb).
# Bucket names are global across all AWS accounts, so AWS appends a unique suffix to the prefix.

resource "aws_s3_bucket" "main" {
  bucket_prefix = "${local.name_prefix}-data-"
  force_destroy = true # lets `terraform destroy` empty a versioned bucket; evidence is exported before teardown

  tags = { Name = "${local.name_prefix}-data" }
}

# Refuse every form of public access, whatever any later policy or ACL says.
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# ACLs off: access is decided only by IAM and the bucket policy.
resource "aws_s3_bucket_ownership_controls" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Keep previous versions, so an overwritten or deleted dataset file can be recovered.
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption at rest with S3-managed keys (no customer-managed KMS key; see the plan's "Not built").
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Cost control: old versions expire after 7 days; unfinished uploads are cleaned up after 1 day.
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = aws_s3_bucket.main.id

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
      aws_s3_bucket.main.arn,
      "${aws_s3_bucket.main.arn}/*",
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
  bucket = aws_s3_bucket.main.id
  policy = data.aws_iam_policy_document.bucket_tls_only.json

  # S3 rejects simultaneous changes to one bucket's settings; apply the policy after public access is blocked.
  depends_on = [aws_s3_bucket_public_access_block.main]
}

# The 3D viewer fetches .glb models from JavaScript, which needs CORS; <img> tags do not.
# Only the shop's own HTTPS origin, read-only. Created once var.app_hostname is set.
resource "aws_s3_bucket_cors_configuration" "main" {
  count  = var.app_hostname == null ? 0 : 1
  bucket = aws_s3_bucket.main.id

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
