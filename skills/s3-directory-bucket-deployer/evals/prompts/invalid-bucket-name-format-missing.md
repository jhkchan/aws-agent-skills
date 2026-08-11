# Eval prompt: invalid-bucket-name-format-missing

Design a deployment plan for an S3 Express One Zone directory bucket.
Emit the standard VERDICT block (DIRECTORY_BUCKET_SPEC, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- Desired bucket name: my-fast-bucket-use1-az1
- AZ: us-east-1a
- Region: us-east-1
- Operator wants to use `aws s3api create-bucket` because the name
  doesn't seem to need special formatting
- Compute: 2 x c7n.large in use1-az1 (subnet subnet-aaa)
- Workload: application cache

Additional context: the operator is new to S3 Express One Zone and
assumed the bucket name is a free-form string. The desired name
`my-fast-bucket-use1-az1` does NOT follow the required directory
bucket name format (`base-name--az-id--x-s3`). The operator plans to
use `create-bucket` if the special format is unnecessary.
