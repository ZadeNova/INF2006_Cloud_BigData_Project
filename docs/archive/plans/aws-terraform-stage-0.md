# Stage 0 guide: install Terraform and pin the provider

Part of [aws-terraform.md](aws-terraform.md). Creates **no AWS resources** and costs nothing. Run everything on the Fedora laptop (the apply device). About 20 minutes.

## What Terraform is

You describe the infrastructure you want in `.tf` files ("a VPC with this CIDR, an RDS instance of this size"). Terraform compares that description with what it created before and works out the difference.

| Word | Meaning |
|---|---|
| **Provider** | A plugin that knows how to talk to one platform's API. We use `hashicorp/aws`. Terraform itself knows nothing about AWS. |
| **Resource** | Something Terraform creates and owns (`resource "aws_vpc" "main" { ... }`). |
| **Data source** | Something Terraform only reads and never creates (`data "aws_iam_instance_profile" "lab"`), such as `LabInstanceProfile`. |
| **State** (`terraform.tfstate`) | Terraform's record of which real resource IDs match which resources in your code. Without it, Terraform thinks nothing exists yet. It stays on this laptop only. |
| **Root module** | The folder you run Terraform in: `src/infrastructure/`. Terraform reads every `.tf` file in the folder together, so how you split the code across files doesn't matter to it. |

The loop you'll repeat every stage:

```
write .tf  →  fmt  →  validate  →  plan -out=x.tfplan  →  read the plan  →  apply x.tfplan
```

- `plan` changes nothing; it shows what `apply` would do.
- `apply` of a saved plan does exactly that plan and nothing else.
- `+` means create, `~` means change in place, `-/+` means **replace** (destroy, then create again; watch for this on RDS), and `-` means destroy.

## Steps

### 1. Install Terraform (Fedora 43, dnf5)

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
sudo dnf install -y terraform
terraform version
```

If HashiCorp's repository doesn't have a Fedora 43 build yet, download the Linux amd64 zip from developer.hashicorp.com/terraform/install and put the `terraform` binary in `~/.local/bin`.

Optional: `terraform -install-autocomplete`, then open a new shell.

### 2. Create the folder and the two stage 0 files

`src/infrastructure/` is already excluded from the Docker image by `src/.dockerignore`.

`src/infrastructure/versions.tf`, which pins what versions may be used:

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

`~> 6.0` allows 6.x but never 7.0, because major versions can change how resources behave. The exact version Terraform picks is recorded in `.terraform.lock.hcl` (step 3).

`src/infrastructure/providers.tf`, which sets up the AWS provider:

```hcl
locals {
  # Every resource name and tag is built from this, so the group number changes in one place.
  name_prefix = "inf2006-grp21"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = local.name_prefix
      Env       = "evidence"
      ManagedBy = "terraform"
    }
  }
}
```

`default_tags` puts these tags on every resource that supports tags. They're how you find everything at teardown, and how you'd find it if the state were ever lost. `local.name_prefix` (added when the team added its group number to every resource name) is a **local value**: computed once from a literal here, then reused everywhere instead of retyping `"inf2006-grp21"` in every file.

`src/infrastructure/variables.tf` (it grows in later stages):

```hcl
variable "region" {
  description = "AWS region. The Learner Lab only offers us-east-1; production would use ap-southeast-1."
  type        = string
  default     = "us-east-1"
}
```

### 3. Initialise

```bash
cd src/infrastructure
terraform init
```

This downloads the AWS provider into `.terraform/` (ignored by git) and writes `.terraform.lock.hcl` (**committed**), which records the exact version and checksums. It needs no AWS credentials.

To let the lock file verify on your other devices' platforms too, run this once:

```bash
terraform providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=windows_amd64
```

Keep only the platforms you actually use.

### 4. Check

```bash
terraform fmt -check      # no output means the files are formatted correctly (run `terraform fmt` to fix)
terraform validate        # "Success! The configuration is valid."
git status                # shows the three .tf files and .terraform.lock.hcl, but no .terraform/ or tfstate
```

Don't run `plan` yet. There's nothing to plan, and it needs lab credentials.

### 5. Your other devices

Once the laptop's commit is pushed:

```bash
git pull && cd src/infrastructure
terraform init -backend=false   # downloads the provider, touches no state
terraform validate
```

They never export lab credentials and never run `plan` or `apply`.

## Acceptance

- [ ] `terraform version` shows ≥ 1.10.
- [ ] `terraform validate` succeeds.
- [ ] `git status` shows no `.terraform/` and no `*.tfstate*`.
- [ ] `versions.tf`, `providers.tf`, `variables.tf` and `.terraform.lock.hcl` are committed.
- [ ] Tick stage 0 in [aws-terraform.md](aws-terraform.md#open-items-per-stage-27-september-2026) and update its status line.

## Next

Stage 1 (network, security groups, S3, ECR, secret, log group, SNS). Its open items are closed before any code for that stage is written.
