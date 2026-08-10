# Organizations Tag Policies Reference

Supplementary reference for the Tag Governance Automator skill. Use
when authoring or debugging an Organizations TagPolicy, designing the
cascade across root/OU/account, or verifying enforcement.

## TagPolicy JSON structure

```json
{
  "tags": {
    "<TagKey>": {
      "tag_key": {
        "case_sensitive": <true|false>
      },
      "allowed_values": ["<value1>", "<value2>"],
      "enforced_for": ["<service>:<resource-type>"]
    }
  }
}
```

### Field reference

| Field | Purpose | Default |
|---|---|---|
| `tag_key.case_sensitive` | Whether the tag KEY matching is case-sensitive (NOT the value) | `false` |
| `allowed_values` | List of permitted tag values; omit for any-value (key-presence-only) | (any value) |
| `enforced_for` | Resource types where the policy blocks non-compliant tag ops | (not enforced) |

**Case sensitivity nuance:**
- `case_sensitive: false` (default) means the tag key `Environment`
  and `environment` are treated as the same key.
- `allowed_values` matching is ALWAYS case-insensitive in the tag
  policy evaluation layer — the policy does NOT enforce value casing.
  To enforce value casing (e.g., `prod` not `Prod`), use a Config
  custom rule with `StringEquals` on the tag value.

## Cascade semantics

Tag policies are evaluated as a UNION down the org tree:

```
Org root policy: Environment allowed_values = ["dev", "prod"]
  └─ OU policy: Environment allowed_values = ["dev", "prod", "staging"]
       └─ Account policy: Environment enforced_for = ["ec2:instance"]
```

Effective policy on the account: `allowed_values = ["dev", "prod"]`
(parent wins — child CANNOT extend). `enforced_for` is additive
(account adds `ec2:instance`).

**Key rules:**
1. A child cannot RELAX a parent's `allowed_values`.
2. A child cannot RELAX a parent's `enforced_for`.
3. A child CAN ADD to `enforced_for` (stricter enforcement).
4. If the root has NO policy, OU/account policies are evaluated
   independently.

## Common `enforced_for` resource type strings

| Service | Resource type string |
|---|---|
| EC2 Instance | `ec2:instance` |
| EC2 Volume | `ec2:volume` |
| S3 Bucket | `s3:bucket` |
| Lambda Function | `lambda:function` |
| RDS DB Instance | `rds:db-instance` |
| DynamoDB Table | `dynamodb:table` |
| ELB (v2) | `elasticloadbalancing:loadbalancer` |
| KMS Key | `kms:key` |
| VPC | `ec2:vpc` |
| Subnet | `ec2:subnet` |
| Security Group | `ec2:security-group` |
| ECR Repository | `ecr:repository` |
| ECS Cluster | `ecs:cluster` |
| EKS Cluster | `eks:cluster` |
| CloudWatch Log Group | `logs:log-group` |

Full list: AWS Service Authorization Reference → "Actions, resources,
and condition keys for AWS services" → look for the service's
`CreateTags` / `TagResource` action resource-type column.

## CLI operations

```bash
# Enable tag policies at root (one-time)
aws organizations enable-policy-type \
  --root-id r-xxxx --policy-type TAG_POLICY

# Create a tag policy
aws organizations create-policy \
  --type TAG_POLICY \
  --name baseline-tag-policy \
  --content file://tag-policy.json

# List existing tag policies
aws organizations list-policies --filter TAG_POLICY

# Describe a policy (view content)
aws organizations describe-policy --policy-id p-xxxxxxx

# Attach to root, OU, or account
aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx

# Detach
aws organizations detach-policy --policy-id p-xxxxxxx --target-id r-xxxx

# Update policy content
aws organizations update-policy --policy-id p-xxxxxxx --content file://tag-policy-v2.json
```

## Effective policy discovery

To see the effective tag policy for a specific account or OU (union
of all attached policies):

```bash
aws organizations describe-effective-policy \
  --organization-resource-id <account-id-or-ou-id>
```

This returns the merged JSON that actually applies. Always verify the
effective policy on a target account before assuming enforcement.

## Tag policy violations (what gets blocked)

When a tag policy with `enforced_for` is active, these API calls are
blocked if the tag violates the policy:

| Service | Blocked API |
|---|---|
| EC2 | `CreateTags`, `RunInstances` (with tags in launch template) |
| S3 | `PutBucketTagging` |
| Lambda | `TagResource`, `CreateFunction20150331` (with tags) |
| RDS | `AddTagsToResource`, `CreateDBInstance` (with tags) |
| Any (via Tagging API) | `resourcegroupstaggingapi:TagResources` |

The error is `TagPolicyViolationException`. The error message names
the violated tag key and the non-compliant value.

**Important:** the policy does NOT block resources created WITHOUT
tags. It only blocks tag operations that use non-compliant values. To
require tag presence, use Config `required-tags` (Step 5 of SKILL.md).

## Tag policy does NOT do

- Retroactively fix existing non-compliant resources (use Config + remediation).
- Enforce case sensitivity of tag VALUES (use Config custom rule).
- Apply to AWS-generated tags (`aws:createdBy`, `aws:cloudformation:*`).
- Cross-account enforcement (each account sees the effective policy;
  cross-account tag operations are governed by IAM, not tag policy).
- Report compliance (tag policy is an enforcement gate, not a
  reporting engine — use Config + Security Hub for reporting).

## Testing a tag policy before promotion

1. Attach to a sandbox OU (`ou-xxxx-sandbox`).
2. Attempt to create a resource with a non-compliant tag value:
   ```bash
   aws ec2 create-tags --resources i-test --tags Key=Environment,Value=INVALID
   # Expected: TagPolicyViolationException
   ```
3. Attempt with a compliant value:
   ```bash
   aws ec2 create-tags --resources i-test --tags Key=Environment,Value=prod
   # Expected: success
   ```
4. Verify effective policy:
   ```bash
   aws organizations describe-effective-policy --organization-resource-id <sandbox-account-id>
   ```
5. Only after all tests pass, promote to root:
   ```bash
   aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx
   ```
