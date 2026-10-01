# Route 53 hosted zone for the team's domain (ADR-003). Create it first and see whether the lab allows it.
# Only after this applies, set the four name_servers below at Namecheap (Domain List > Manage > Nameservers >
# Custom DNS). Do not change them before: after delegation Namecheap's own records stop applying.
# The zone stays up between experiments; a recreated zone gets new name servers, so destroy it only at final teardown.

resource "aws_route53_zone" "main" {
  name    = var.domain_name
  comment = "${local.name_prefix}: zone for the shop and its certificate validation"

  # Lets the final teardown delete the zone even if records remain (all of them are Terraform-managed).
  force_destroy = true

  tags = { Name = "${local.name_prefix}-zone" }
}
