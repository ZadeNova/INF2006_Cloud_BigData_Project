# web-entry: the front door both variants share (ADR-014)

Everything in front of the application, identical for `ec2/` and `fargate/` by construction: `sg-alb` and `sg-app`
with their rules (and the stack's own rule on `base/`'s `sg-db`), the ALB with its HTTPS listener and 80 redirect,
the target group and `/health/` check, the WAF rate rule on `POST /login/`, three alarms and two saved log queries,
the log group, the Route 53 alias record, and the application's non-secret environment.

A stack calls it once and adds only its own compute and scaling:

```hcl
module "web_entry" {
  source = "../modules/web-entry"
  name = local.stack_prefix, stack = "ec2", target_type = "instance", ...
}
```

| Input | Meaning |
|---|---|
| `name`, `stack` | Resource name prefix (`inf2006-grp21-ec2`) and stack key |
| `region`, `hostname`, `release_id` | Go into the app's environment |
| `target_type` | `instance` (Auto Scaling group) or `ip` (Fargate tasks) |
| `vpc_id`, `public_subnet_ids`, `sg_db_id`, `certificate_arn`, `zone_id`, `sns_topic_arn` | From `base/` |
| `waf_login_limit`, `waf_login_action` | ADR-012 |

Outputs the compute needs: `app_security_group_id`, `target_group_arn`, `log_group_name`, `app_environment`. Outputs for
scaling: `alb_arn_suffix`, `target_group_arn_suffix`; for the stacks' outputs: `alb_dns_name`, `alb_security_group_id`, `web_acl_name`.

The module configures no provider; it uses the one in the calling folder (region and default tags).
