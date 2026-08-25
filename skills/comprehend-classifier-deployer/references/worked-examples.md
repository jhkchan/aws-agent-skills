# Worked Examples (load on demand) — Comprehend Classifier Deployer

Training-job CLI variant with KMS encryption and VPC config, moved verbatim from SKILL.md. The primary worked example output stays in SKILL.md.


---

## Step 4 — Training job variant with KMS encryption and VPC config (moved from SKILL.md)

**With KMS encryption and VPC config:**

```bash
CLASSIFIER_ARN=$(aws comprehend create-document-classifier \
  --document-classifier-name "secure-classifier" \
  --data-format COMPREHEND_CSV \
  --input-data-config S3Uri=s3://my-bucket/comprehend/training/training.csv \
  --document-classifier-config "Mode=MULTI_CLASS,LanguageCode=en" \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendRole \
  --model-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --volume-kms-key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234 \
  --vpc-config '{"SecurityGroupIds":["sg-abc123"],"Subnets":["subnet-aaa","subnet-bbb"]}' \
  --region us-east-1 \
  --query 'DocumentClassifierArn' --output text)
```
