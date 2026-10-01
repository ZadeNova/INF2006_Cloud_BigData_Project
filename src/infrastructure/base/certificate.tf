# One ACM certificate for both shop hostnames, validated by DNS records in the Route 53 zone (ADR-006).
# The certificate lives in base/ so a recreated ALB in either stack just attaches it; the validation records
# are permanent, so a certificate that is already issued never needs a manual step again.

locals {
  # One name per stack. Each stack adds its own alias record for its own name (dns.tf is the zone only).
  shop_hostnames = {
    ec2     = "shop-ec2.${var.domain_name}"
    fargate = "shop-fargate.${var.domain_name}"
  }
}

resource "aws_acm_certificate" "shop" {
  domain_name               = local.shop_hostnames.ec2
  subject_alternative_names = [local.shop_hostnames.fargate]
  validation_method         = "DNS"

  # A replacement certificate must exist before the old one is removed, or an ALB attached to it blocks the destroy.
  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = "${local.name_prefix}-cert-shop" }
}

# One CNAME per name, built from what ACM asks for. allow_overwrite so a rerun after a half-failed apply adopts
# a record that already exists instead of failing.
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for o in aws_acm_certificate.shop.domain_validation_options : o.domain_name => {
      name   = o.resource_record_name
      type   = o.resource_record_type
      record = o.resource_record_value
    }
  }

  zone_id         = aws_route53_zone.main.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

# Waits until ACM reports ISSUED. This is the step that only succeeds once the Namecheap name servers are live.
resource "aws_acm_certificate_validation" "shop" {
  certificate_arn         = aws_acm_certificate.shop.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}
