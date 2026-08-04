# AWS CLI Reference — Shared Commands

**Why this file exists:** Cross-cutting CLI reference loaded by any skill that
needs to query AWS state. The specific audit logic (which commands to run,
what output to check) lives in each specialist's `references/` directory. This
file covers the shared patterns: how to enumerate resources safely, how to
handle pagination, and the common pre-flight checks.

---

## Resource enumeration patterns (Phase 1: Assess)

### S3

```bash
# List all buckets in the account
aws s3api list-buckets --query 'Buckets[].Name' --output table

# Check account-level BPA
aws s3control get-public-access-block --account-id <account-id>

# Check bucket-level BPA for a specific bucket
aws s3api get-public-access-block --bucket <bucket-name>

# Get bucket policy (may fail if no policy attached)
aws s3api get-bucket-policy --bucket <bucket-name> --output json

# Get bucket ACL
aws s3api get-bucket-acl --bucket <bucket-name>
```

### IAM

```bash
# List all roles
aws iam list-roles --query 'Roles[].RoleName' --output table

# Get a role's inline policies
aws iam list-role-policies --role-name <role-name>

# Get inline policy document
aws iam get-role-policy --role-name <role-name> --policy-name <policy-name>

# Get attached managed policies
aws iam list-attached-role-policies --role-name <role-name>

# Get managed policy document
aws iam get-policy-version --policy-arn <arn> --version-id v1
```

### EC2

```bash
# List all security groups
aws ec2 describe-security-groups --query 'SecurityGroups[].{Name:GroupName,Id:GroupId}' --output table

# Get detailed rules for a specific security group
aws ec2 describe-security-groups --group-ids <sg-id> --output json

# List security groups with 0.0.0.0/0 inbound rules
aws ec2 describe-security-groups --filters Name=ip-permission.cidr,Values=0.0.0.0/0 --output json
```

## Pagination pattern

Most list/describe commands return paginated results. Always use `--query` with
the AWS CLI's built-in auto-pagination:

```bash
# Auto-paginate (CLI handles it)
aws iam list-roles --output json > all-roles.json

# Manual pagination (for large result sets)
aws s3api list-objects-v2 --bucket <bucket> --starting-token <next-token>
```

## Pre-flight safety checks (before any remediation)

```bash
# Verify the resource exists
aws s3api head-bucket --bucket <name>
aws iam get-role --role-name <name>
aws ec2 describe-security-groups --group-ids <sg-id>

# Capture current state for rollback
aws s3api get-bucket-policy --bucket <name> --output json > /tmp/<name>-policy-backup-$(date +%s).json
aws iam get-role-policy --role-name <name> --policy-name <policy> > /tmp/<name>-policy-backup-$(date +%s).json
aws ec2 describe-security-groups --group-ids <sg-id> --output json > /tmp/<sg-id>-backup-$(date +%s).json

# Verify your AWS identity (which account are you operating on?)
aws sts get-caller-identity
```

## Output format conventions

All auditor skills use these output formats for consistency:

- **JSON** for data capture (policy documents, rule sets)
- **Table** for human-readable summaries (resource lists, verdict tables)
- **Text** for single-value queries (bucket names, role ARNs)

The per-resource VERDICT format is standardized across all skills:

```text
RESOURCE: <name>
VERDICT: <SAFE | PUBLIC | OPEN | OVERPERMISSIVE | AMBIGUOUS | RESTRICTED>
REASON: <1-2 sentences citing the specific config and the rule number>
REMEDIATION: <specific action, or "None required">
```
