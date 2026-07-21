#!/usr/bin/env bash
# EdgeWay bulut altyapisi: bucket + sifreleme + lifecycle + cihaz IAM kullanicisi.
# Kullanim: ./bootstrap_aws.sh <bucket> [region] [device-id]
# NOT: sonda basilan erisim anahtari BIR KEZ gosterilir — guvenli sakla, chat'e yapistirma.
set -euo pipefail
command -v aws >/dev/null || { echo "HATA: aws cli yok — once: brew install awscli && aws configure"; exit 1; }
BUCKET="${1:?kullanim: ./bootstrap_aws.sh <bucket> [region] [device-id]}"
REGION="${2:-eu-central-1}"
DEVICE="${3:-edgeway-rpi-01}"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "bucket zaten var: $BUCKET"
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
fi
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" \
  --lifecycle-configuration "file://$(dirname "$0")/s3_lifecycle.json"

PNAME="${BUCKET}-${DEVICE}"
PDOC=$(cat << JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["s3:PutObject","s3:GetObject","s3:AbortMultipartUpload"],
  "Resource":"arn:aws:s3:::${BUCKET}/*"},
 {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":"arn:aws:s3:::${BUCKET}"}]}
JSON
)
PARN=$(aws iam create-policy --policy-name "$PNAME" --policy-document "$PDOC" \
  --query Policy.Arn --output text 2>/dev/null || \
  aws iam list-policies --scope Local --query "Policies[?PolicyName=='$PNAME'].Arn" --output text)
aws iam create-user --user-name "$DEVICE" 2>/dev/null || echo "kullanici zaten var: $DEVICE"
aws iam attach-user-policy --user-name "$DEVICE" --policy-arn "$PARN"
echo
echo "=== bucket hazir: $BUCKET ($REGION) — KVKK: region secimi sozlesmeye ==="
echo "=== cihaz anahtari (AccessKeyId  SecretAccessKey) — BIR KEZ, guvenli sakla ==="
aws iam create-access-key --user-name "$DEVICE" \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text
