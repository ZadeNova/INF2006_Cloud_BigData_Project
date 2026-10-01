# The VPC: the team's private network. Nothing gets in or out until the gateway below is attached.
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true # RDS endpoint names and verify-full TLS need DNS hostnames

  tags = { Name = "${local.name_prefix}-vpc" }
}

# The VPC's one door to the internet. Only subnets whose route table points here are public.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-igw" }
}

locals {
  # One public and one private subnet per AZ. Keys ("a", "b") become part of each resource's address.
  public_subnets = {
    a = { az = var.availability_zones[0], cidr = "10.0.1.0/24" }
    b = { az = var.availability_zones[1], cidr = "10.0.2.0/24" }
  }
  private_subnets = {
    a = { az = var.availability_zones[0], cidr = "10.0.11.0/24" }
    b = { az = var.availability_zones[1], cidr = "10.0.12.0/24" }
  }
}

# Public subnets: each stack's ALB and app compute. No automatic public IPs; the stack asks for one.
resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id                  = aws_vpc.main.id
  availability_zone       = each.value.az
  cidr_block              = each.value.cidr
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-public-${each.key}", Tier = "public" }
}

# Private subnets: RDS only. No route to the internet in either direction.
resource "aws_subnet" "private" {
  for_each = local.private_subnets

  vpc_id            = aws_vpc.main.id
  availability_zone = each.value.az
  cidr_block        = each.value.cidr

  tags = { Name = "${local.name_prefix}-private-${each.key}", Tier = "private" }
}

# Public route table: everything not inside the VPC goes to the internet gateway.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name_prefix}-rt-public" }
}

# Private route table: only the implicit local route, so traffic stays inside the VPC.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-rt-private" }
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}
