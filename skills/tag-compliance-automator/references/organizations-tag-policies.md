# Organizations Tag Policies Reference

Supplementary reference for the Tag Compliance Automator skill. Use
when designing an Organizations TagPolicy, deciding `enforced_for`
coverage, or debugging a policy that is not enforcing as expected.

## TagPolicy JSON structure

A TagPolicy `content` field is a JSON document with a `tags` object.
Each key under `tags` declares the rules for one tag key.

```json
{
  "tags": {
    "Environment": {
      "TagKey": "Environment",
      "ExpectedStringValues": ["dev", "staging", "prod"],
      "EnforcedFor": [
        "AWS::EC2::Instance",
        "AWS::S3::Bucket",
        "AWS::RDS::DBInstance",
        "AWS::Lambda::Function"
      ]
    },
    "CostCenter": {
      "TagKey": "CostCenter",
      "ExpectedStringValues": ["cc-100", "cc-200", "cc-300"],
      "EnforcedFor": ["AWS::EC2::Instance", "AWS::S3::Bucket"]
    },
    "Owner": {
      "TagKey": "Owner",
      "EnforcedFor": ["AWS::EC2::Instance"]
    }
  }
}
```

| Field | Purpose | Required |
|---|---|---|
| `tags.<Key>.TagKey` | The tag key name (must match `<Key>`) | Yes |
| `tags.<Key>.ExpectedStringValues` | Allowed values list | No (presence-only if omitted) |
| `tags.<Key>.EnforcedFor` | Resource types that MUST comply | Yes for enforcement |
| `tags.<Key>.CaseSensitive` | Key/value case sensitivity (default: true) | No |

## Enforcement semantics

- **Without `EnforcedFor`**: the policy is advisory. AWS does not block
  non-compliant tag operations. Config rules may still flag the resource
  as NON_COMPLIANT, but the create/modify operation succeeds.
- **With `EnforcedFor`**: AWS returns `ConstraintViolation` on any tag
  operation that violates the policy for the listed resource types.
  This includes creating a resource without the required key or setting
  a value outside `ExpectedStringValues`.

## Effective policy inheritance

Tag policies cascade from root to OU to account. The effective policy
for an account is the policy attached to its closest ancestor (root or
OU). Child-OU policies OVERRIDE root policies — they do NOT merge.

| Attachment | Effective for accounts under it |
|---|---|
| Root only | Root policy |
| Root + OU | OU policy (root keys are lost unless re-declared in OU) |
| Root + account | Account policy (root keys are lost unless re-declared) |

To add a key at the OU level without losing root keys, re-declare every
parent key in the OU policy.

## Supported resource types for EnforcedFor

The `EnforcedFor` field accepts resource types in `AWS::service::resource`
format. Common types:

| Resource type | Notes |
|---|---|
| `AWS::EC2::Instance` | EC2 instances |
| `AWS::EC2::Volume` | EBS volumes |
| `AWS::EC2::NetworkInterface` | ENIs |
| `AWS::S3::Bucket` | S3 buckets (object tags are not policy-enforced) |
| `AWS::RDS::DBInstance` | RDS instances |
| `AWS::Lambda::Function` | Lambda functions |
| `AWS::DynamoDB::Table` | DynamoDB tables |

The full list expands quarterly. Always cross-reference the AWS
documentation for the current supported set.

## Case sensitivity matrix

Tag policies, Config rules, Cost Explorer, and the Resource Groups
Tagging API interpret case independently:

| System | Default case sensitivity | Override |
|---|---|---|
| Organizations TagPolicy | `case_sensitive: true` | Set `CaseSensitive: false` per key |
| Config `required-tags` | Exact match on InputParameters key | No override |
| Config `allowed-tag-values` | Exact match on key and value | No override |
| Cost Explorer (user-defined) | Case-insensitive on key, case-sensitive on value | No override |
| Resource Groups Tagging API | Case-sensitive on key | No override |

A mismatch between the TagPolicy setting and the Config InputParameters
key name produces conflicting compliance reports.
