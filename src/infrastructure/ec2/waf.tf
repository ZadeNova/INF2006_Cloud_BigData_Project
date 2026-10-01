# One regional web ACL on the ALB with one rate-based rule on POST /login/ (ADR-012). It answers threat T7
# (credential stuffing and password guessing). Count mode first; block mode is the same rule with a different action.

resource "aws_wafv2_web_acl" "app" {
  name        = "${local.stack_prefix}-waf"
  description = "Rate limit on POST /login/ per client IP"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "login-rate-limit"
    priority = 1

    action {
      dynamic "count" {
        for_each = var.waf_login_action == "count" ? [1] : []
        content {}
      }
      dynamic "block" {
        for_each = var.waf_login_action == "block" ? [1] : []
        content {}
      }
    }

    statement {
      rate_based_statement {
        limit                 = var.waf_login_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300

        # Only POST requests to exactly /login/ count towards the limit; browsing is never limited.
        scope_down_statement {
          and_statement {
            statement {
              byte_match_statement {
                search_string         = "/login/"
                positional_constraint = "EXACTLY"
                field_to_match {
                  uri_path {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
            statement {
              byte_match_statement {
                search_string         = "POST"
                positional_constraint = "EXACTLY"
                field_to_match {
                  method {}
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
              }
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.stack_prefix}-login-rate"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.stack_prefix}-waf"
    sampled_requests_enabled   = true
  }

  tags = { Name = "${local.stack_prefix}-waf" }
}

resource "aws_wafv2_web_acl_association" "app" {
  resource_arn = aws_lb.app.arn
  web_acl_arn  = aws_wafv2_web_acl.app.arn
}
