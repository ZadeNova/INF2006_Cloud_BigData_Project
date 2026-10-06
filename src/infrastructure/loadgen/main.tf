# The load generator (ADR-013): one instance in the same region as the app, so the traffic does not cross the
# internet from the laptop and the results measure the app, not the home connection. It is its own stack so it is up
# only during test sessions (about USD 0.085 an hour, unverified) and does not change the comparison between ec2/
# and fargate/. The harness is copied onto it through the project bucket; a shell is opened with Session Manager.

resource "aws_security_group" "loadgen" {
  name        = "${local.stack_prefix}-sg"
  description = "Load generator: no inbound, HTTPS out"
  vpc_id      = local.base.vpc_id

  tags = { Name = "${local.stack_prefix}-sg" }
}

# No inbound rules at all: Session Manager connects outward from the instance.
resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.loadgen.id
  description       = "HTTPS to the shop under test, AWS APIs, S3 and package mirrors"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_instance" "loadgen" {
  ami                         = data.aws_ssm_parameter.al2023_ami.insecure_value # an AMI ID, not a secret
  instance_type               = var.instance_type
  subnet_id                   = local.base.public_subnet_ids["a"]
  vpc_security_group_ids      = [aws_security_group.loadgen.id]
  associate_public_ip_address = true # reaches the shop, S3 and SSM without a NAT gateway
  iam_instance_profile        = data.aws_iam_instance_profile.lab.name

  # IMDSv2 only, as on the app instances. Hop limit 1: nothing here runs in a container.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = 16
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data                   = file("${path.module}/user_data.sh")
  user_data_replace_on_change = true

  # A newer Amazon Linux release must not replace the generator in the middle of a campaign: every run's metadata
  # records the generator it ran on, and the runs of one campaign should share it. Replace deliberately with
  # `terraform apply -replace=aws_instance.loadgen`.
  lifecycle {
    ignore_changes = [ami]
  }

  tags = { Name = local.stack_prefix }
}
