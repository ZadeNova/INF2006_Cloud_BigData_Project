#!/usr/bin/env bash
# Build (if needed), push and release-tag the app image, then tell Terraform which tag to run (ADR-005).
#
#   scripts/push-image.sh [git-sha]     default: the current HEAD, short form
#
# Tags are immutable in ECR, so a git-SHA tag always means one image. If <sha> is already in ECR it is NOT
# rebuilt: it only gets its release-<sha> tag (the tag the lifecycle policy protects) and is reported.
# A new image is built only for the current HEAD, from a clean tree. The backend is frozen: this builds
# src/Dockerfile exactly as committed and changes nothing in it.
# Writes image.auto.tfvars (git-ignored) into ec2/ and fargate/, so both stacks run the same release.
# Prints the image digest; record it in the runbook. Needs: lab credentials, docker, aws, terraform, git.
set -euo pipefail

INFRA="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$(cd "$INFRA/.." && pwd)"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
die() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

aws sts get-caller-identity --query Account --output text >/dev/null 2>&1 \
  || die "no working lab credentials in this shell (run labcreds first)"
HEAD_SHA="$(git -C "$INFRA" rev-parse --short HEAD)"
SHA="${1:-$HEAD_SHA}"
REPO_URL="$(terraform -chdir="$INFRA/base" output -raw ecr_repository_url)"
REPO="${REPO_URL#*/}"; REGISTRY="${REPO_URL%%/*}"

have_tag() { aws ecr describe-images --region "$REGION" --repository-name "$REPO" --image-ids "imageTag=$1" >/dev/null 2>&1; }

if have_tag "$SHA"; then
  echo "Image $SHA is already in ECR; not rebuilding."
else
  [ "$SHA" = "$HEAD_SHA" ] || die "image $SHA is not in ECR and is not the current commit ($HEAD_SHA); check out that commit to build it"
  [ -z "$(git -C "$SRC" status --porcelain -- . ':!infrastructure')" ] || die "uncommitted changes under src/ (outside infrastructure/); commit first"
  aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
  docker build -t "$REPO_URL:$SHA" -f "$SRC/Dockerfile" "$SRC"
  docker push "$REPO_URL:$SHA"
fi

if have_tag "release-$SHA"; then
  echo "release-$SHA already exists."
else
  MANIFEST="$(aws ecr batch-get-image --region "$REGION" --repository-name "$REPO" --image-ids "imageTag=$SHA" \
    --query 'images[0].imageManifest' --output text)"
  aws ecr put-image --region "$REGION" --repository-name "$REPO" --image-tag "release-$SHA" --image-manifest "$MANIFEST" >/dev/null
  echo "tagged release-$SHA"
fi

DIGEST="$(aws ecr describe-images --region "$REGION" --repository-name "$REPO" --image-ids "imageTag=release-$SHA" \
  --query 'imageDetails[0].imageDigest' --output text)"
for stack in ec2 fargate; do
  [ -d "$INFRA/$stack" ] && printf 'image_tag = "release-%s"\n' "$SHA" > "$INFRA/$stack/image.auto.tfvars"
done
echo "Release: release-$SHA"
echo "Digest:  $DIGEST"
echo "Stacks that exist now read image_tag from image.auto.tfvars. Record the digest in evidence/aws-build-runbook.md."
