#!/usr/bin/env bash
set -euo pipefail
BUCKET="${1:?kullanim: ./bootstrap_aws.sh <bucket-adi> [region]}"
REGION="${2:-eu-central-1}"
aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" --lifecycle-configuration file://s3_lifecycle.json
echo "bucket hazir: $BUCKET ($REGION) — KVKK notu: region secimini musteri sozlesmesine yaz"
