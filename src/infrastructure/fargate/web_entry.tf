# Everything in front of the app is the shared module (ADR-014): security groups, ALB, HTTPS, health check, WAF,
# alarms, log group and the DNS alias. This stack adds its own compute (ecs.tf) and scaling (scaling.tf).

module "web_entry" {
  source = "../modules/web-entry"

  name        = local.stack_prefix
  stack       = "fargate"
  region      = var.region
  hostname    = local.app_hostname
  release_id  = var.image_tag
  target_type = "ip" # awsvpc: the ALB registers each task's own network interface

  vpc_id            = local.base.vpc_id
  public_subnet_ids = values(local.base.public_subnet_ids)
  sg_db_id          = local.base.sg_db_id
  certificate_arn   = local.base.certificate_arn
  zone_id           = local.base.route53_zone_id
  sns_topic_arn     = local.base.sns_topic_arn

  waf_login_limit  = var.waf_login_limit
  waf_login_action = var.waf_login_action
}
