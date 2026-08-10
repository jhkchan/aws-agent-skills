---
name: tag-governance-automator
description: >-
  Designs and implements AWS tag governance automation across Organizations
  TagPolicy JSON (allowed_values, case_sensitive, enforced_for cascade),
  EventBridge + Lambda auto-tagging on EC2/S3/Lambda creation (derive Owner
  from IAM identity, Environment from account map), Resource Groups Tagging
  API bulk operations (tag-resources, untag-resources, get-resources
  multi-region), Config required-tags managed rule + Security Hub finding
  aggregation, cost-allocation-tag activation via Billing API (user-defined
  vs AWS-generated), and ABAC IAM policy design with aws:ResourceTag and
  aws:PrincipalTag condition keys. Covers automated remediation: Config
  detects missing tag, SSM Automation adds tag, Config re-evaluates.
  Emits AUTOMATED with tag policy template or MANUAL_STEP_REQUIRED with the
  specific gap. Use when building tag governance, auto-tagging pipelines,
  ABAC, or tag-compliance automation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy design. Live deployment
  uses aws organizations enable-policy-type, create-policy, update-policy,
  aws resourcegroupstaggingapi tag-resources, untag-resources, get-resources,
  aws configservice put-config-rule, describe-config-rules,
  aws ce update-cost-allocation-tags-status, aws ssm create-document,
  start-automation-execution, and aws lambda create-function with an
  EventBridge rule — AWS CLI v2, SSO or key-based credentials,
  Organizations management or member-account permissions.
keywords:
  - AWS Organizations
  - Tag Policy
  - TagPolicy
  - allowed_values
  - enforced_for
  - Resource Groups Tagging API
  - tag-resources
  - untag-resources
  - AWS Config
  - required-tags
  - Security Hub
  - EventBridge
  - Lambda auto-tagging
  - cost allocation tags
  - ABAC
  - aws:ResourceTag
  - aws:PrincipalTag
  - aws:RequestTag
  - SSM Automation
  - tag compliance
  - tag governance
tags: [aws-organizations, tag-policy, resource-groups-tagging-api, aws-config, security-hub, abac, eventbridge, lambda, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATED | MANUAL_STEP_REQUIRED"
  when_to_use: >-
    Designing Organizations tag policies (allowed_values, case sensitivity,
    enforced_for), building EventBridge + Lambda auto-tagging pipelines,
    running Resource Groups Tagging API bulk operations across regions,
    wiring Config required-tags rules with Security Hub findings,
    activating cost allocation tags, designing ABAC IAM policies with
    aws:ResourceTag / aws:PrincipalTag conditions, or remediating untagged
    resources via Config + SSM Automation.
  activation_triggers:
    - "design Organizations TagPolicy"
    - "allowed_values enforced_for"
    - "auto-tag on creation EventBridge Lambda"
    - "Resource Groups Tagging API bulk"
    - "tag-resources untag-resources"
    - "required-tags Config rule"
    - "cost allocation tag activation"
    - "ABAC IAM policy ResourceTag"
    - "tag compliance remediation"
    - "Security Hub tag finding"
    - "tag governance baseline"
  invocation_schema: >-
    Input: either (a) a tag governance requirement ("enforce Environment and
    CostCenter tags on all EC2 and S3 resources", "auto-tag Owner on EC2
    creation", "design ABAC policy for team-scoped access"), OR (b) an
    existing tag policy / Config rule / EventBridge rule to audit and
    harden. Output: deterministic GOVERNANCE block per requirement —
    STRATEGY/POLICY/AUTOMATION/COMPLIANCE/VERDICT — where VERDICT is
    AUTOMATED (tag policy template ready) or MANUAL_STEP_REQUIRED (specific
    gap cited, e.g., Billing console activation that cannot be API-driven).
---

# Tag Governance Automator

## Mindset

**One-line takeaway:** tag governance is a three-layer stack — **define**
(Organizations TagPolicy sets the rules) → **enforce** (EventBridge +
Lambda auto-tags on creation; Config required-tags detects violations) →
**remediate** (SSM Automation or Lambda adds missing tags; Config
re-evaluates and flips COMPLIANT). A gap in ANY layer produces a silent
failure: the policy is published but never enforced, resources are tagged
inconsistently, cost allocation reports are wrong, and ABAC policies
silently over-permit or under-permit.

- **Organizations TagPolicy** without `enforced_for` is advisory only:
  the policy says Environment must be `prod` or `dev`, but if no resource
  type is listed under `enforced_for`, AWS does not block non-compliant
  tag operations. The policy is documentation, not enforcement.
- **Auto-tagging** without a **tag policy** produces drift: the Lambda
  stamps tags on creation, but nothing stops a human from changing them
  afterward. Always pair auto-tagging with a tag policy that prevents
  unauthorized modifications.
- **Cost allocation tags are NOT active by default.** A perfectly tagged
  fleet produces zero cost-dimension data in CUR / Cost Explorer until
  an administrator activates the tag keys in Billing. This is the #1
  "we tagged everything and Cost Explorer is still empty" issue.

## Quick navigation

| You want to... | Go to |
|---|---|
| Define required vs optional tag keys | Step 1 (tag strategy table) |
| Author Organizations TagPolicy JSON | Step 2 + Appendix A |
| Build EventBridge + Lambda auto-tagging | Step 3 + reference auto-tagging-eventbridge-lambda.md |
| Bulk tag/untag across regions via Tagging API | Step 4 |
| Wire Config `required-tags` rule | Step 5 |
| Route tag findings to Security Hub | Step 6 |
| Remediate missing tags automatically (Config → SSM → Config) | Step 7 |
| Activate cost allocation tags | Step 8 |
| Design ABAC IAM policies (aws:ResourceTag / aws:PrincipalTag) | Step 9 |
| Verify and audit a deployed governance baseline | Step 10 |
| Avoid common tag-policy and ABAC pitfalls | Anti-Patterns |
| Recent features (TagPolicy ABAC, CE tag-status API) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **`enforced_for` is what makes a tag policy enforce.** Without it,
   the policy defines allowed values but AWS does not block non-compliant
   `CreateTags` / `PutBucketTagging` / `TagResource` calls. A policy
   with `allowed_values` but no `enforced_for` is a recommendation, not
   a guardrail. Always list the resource types explicitly.
2. **Organizations TagPolicy `allowed_values` matching is case-insensitive
   by default.** Set `tag_key.case_sensitive: true` if your downstream
   systems (CUR, ABAC conditions) depend on exact casing. A mismatch
   between the policy's case sensitivity and your IAM `StringEquals`
   conditions produces silent ABAC over-grants.
3. **Tag policies cascade: org root → OU → account → resource.** A
   child policy does NOT override the parent — it is additive (union of
   constraints). You cannot relax a parent's `allowed_values` at the
   child level. If the root says Environment is `prod|dev`, an OU
   cannot add `staging` without editing the root policy.
4. **Cost allocation tags require explicit activation in Billing.**
   Tagging a resource does NOT make the tag appear in Cost Explorer or
   the Cost and Usage Report (CUR). An administrator must activate each
   tag key via the Billing console or `ce update-cost-allocation-tags-status`.
   Activation takes up to 24 hours to propagate.
5. **ABAC condition keys are case-sensitive at the IAM evaluation layer.**
   `aws:ResourceTag/Environment` with `StringEquals: "prod"` does NOT
   match a resource tagged `Prod`. If your tag policy allows
   case-insensitive values but your IAM condition uses `StringEquals`,
   you have a silent gap. Use `StringEqualsIgnoreCase` for ABAC
   conditions OR enforce case sensitivity in the tag policy.

## Pre-flight: data requirements

Designing a tag governance baseline requires these inputs:

| Input | Source | Why |
|---|---|---|
| Organization ID + root ID | `aws organizations describe-organization` | Tag policy scope |
| Existing tag policies | `aws organizations list-policies --filter TAG_POLICY` | Don't overwrite blindly |
| OU structure | `aws organizations list-organizational-units-for-parent` | Where to attach policies |
| Account → environment mapping | Internal CMDB or account tags | Drives `Environment` allowed_values |
| Config recorder status | `aws configservice describe-configuration-recorders` | Required-tags rule needs recorder |
| Existing Config rules | `aws configservice describe-config-rules` | Avoid duplicate required-tags rules |
| Security Hub enablement | `aws securityhub describe-hub` | Finding aggregation target |
| Sample resource inventory | `aws resourcegroupstaggingapi get-resources` | Baseline current tag coverage |
| IAM principal tags (for ABAC) | `aws iam list-user-tags` / `list-role-tags` | ABAC source attributes |

**If the input is malformed** (missing org ID, ambiguous scope), emit:

```text
GOVERNANCE: <reference>
VERDICT: ERROR
REASON: Cannot design tag governance — Organizations root ID and target scope (resource types + accounts) are required.
GAP: Re-supply describe-organization output and the list of resource types to enforce tagging on.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious TagPolicy + tagging behaviors

These behaviors change the governance design if ignored:

- **Tag policies are enforced only on resource types listed in
  `enforced_for`.** A policy with an `Environment` tag key but
  `enforced_for: ["ec2:instance"]` does NOT enforce on S3 buckets,
  Lambda functions, RDS instances, or any other type. Operators
  frequently publish a policy and assume it covers the full fleet.

- **`enforced_for` uses `service:resource-type` notation** (e.g.,
  `ec2:instance`, `s3:bucket`, `lambda:function`, `rds:db-instance`,
  `dynamodb:table`). A typo (`ec2:Instance` vs `ec2:instance`) silently
  disables enforcement. Always verify with the AWS service authorization
  reference.

- **Tag policies block `CreateTags` / `Put*Tagging` / `TagResource`
  calls that violate the policy** — they do NOT retroactively fix
  existing resources. Resources tagged before the policy was attached
  remain non-compliant until remediated. Use Config + remediation
  (Step 7) to handle the backlog.

- **Resource Groups Tagging API `tag-resources` is NOT atomic.** The
  API returns a `FailedResourcesMap` for resources that could not be
  tagged (permission denied, throttled, wrong region). Always check
  the response — a "successful" call may have partially failed.

- **`resourcegroupstaggingapi get-resources` is region-scoped.** To
  inventory resources across all regions, iterate over
  `ec2 describe-regions` and aggregate. There is no native global
  tag query. A common pitfall is querying only `us-east-1` and
  reporting 100% compliance.

- **Config `required-tags` managed rule checks up to 5 tag keys per
  rule.** If you require more than 5 tags, deploy multiple required-tags
  rules (e.g., `required-tags-core` for 5 keys, `required-tags-ext` for
  the next 5). A single rule silently ignores keys beyond the 5th.

- **Cost allocation tag activation is per-account (not org-level).**
  In an Organization with 50 member accounts, activating the `Owner`
  tag for cost reporting requires activating it in EACH account's
  Billing settings (or via the org payer account's consolidated
  activation if enabled). A single `ce update-cost-allocation-tags-status`
  call applies to the payer account only.

- **ABAC `aws:PrincipalTag` is resolved at session creation.** If you
  change a user's `Team` tag in IAM, existing sessions still carry the
  old value until the session expires or is revoked. ABAC policy
  changes and principal tag changes must be coordinated with session
  refresh.

- **`aws:RequestTag` is only valid on create/tag API calls** (RunInstances,
  CreateBucket, CreateFunction, CreateTags). It cannot be used in a
  policy that governs read operations. A common mistake is writing
  `aws:RequestTag/Environment` into a `Deny` statement for `s3:GetObject`
  — the condition silently never matches.

- **SSM Automation `aws-ApplyEC2Tags` style runbooks do not exist as a
  single managed document for all resource types.** EC2 uses
  `ec2:CreateTags`, S3 uses `s3:PutBucketTagging`, Lambda uses
  `lambda:TagResource`, RDS uses `rds:AddTagsToResource`. A custom
  SSM Automation document must branch by resource type OR you deploy
  one document per resource type.

- **Tag policies do NOT enforce on AWS-generated tags** (e.g.,
  `aws:cloudformation:stack-name`, `aws:createdBy`). These are system
  tags; user-defined tag policies apply only to user-supplied tag keys.

### Step 1: Define the tag strategy framework

Every governance engagement starts with a canonical tag key set.
Default to this baseline and adjust per organizational requirements:

| Tag key | Category | Required? | Allowed values (example) | Purpose |
|---|---|---|---|---|
| `Environment` | Required | Yes | `dev`, `staging`, `prod` | ABAC, cost split, blast-radius scoping |
| `Owner` | Required | Yes | email or team alias (free-form) | Accountability, alert routing |
| `Project` | Required | Yes | project code (free-form) | Cost allocation |
| `CostCenter` | Required | Yes | `cc-1001`, `cc-1002`, ... | Finance reporting |
| `Application` | Required | Yes | app name (free-form) | Grouping, dependency mapping |
| `Backup:Required` | Optional | No | `true`, `false` | Backup policy routing |
| `ComplianceTier` | Optional | No | `tier-1`, `tier-2`, `tier-3` | Audit cadence, SOC scope |
| `DataClassification` | Optional | No | `public`, `internal`, `confidential` | Macie, KMS routing |

**Decision rules:**
- Never exceed 10 required tags — operational friction kills adoption.
- Free-form tags (`Owner`, `Project`) are acceptable for the FIRST pass;
  tighten to allowed_values once the set stabilizes.
- Map each tag key to a downstream consumer (Cost Explorer, ABAC, Config,
  Macie). A tag no consumer reads is dead weight.

### Step 2: Author the Organizations TagPolicy JSON

Enable tag policies at the org root (one-time):

```bash
aws organizations enable-policy-type \
  --root-id r-xxxx \
  --policy-type TAG_POLICY
```

Tag policy JSON template (the canonical baseline):

```json
{
  "tags": {
    "Environment": {
      "tag_key": {
        "case_sensitive": false
      },
      "allowed_values": ["dev", "staging", "prod"],
      "enforced_for": [
        "ec2:instance",
        "ec2:volume",
        "s3:bucket",
        "lambda:function",
        "rds:db-instance",
        "dynamodb:table",
        "elasticloadbalancing:loadbalancer",
        "kms:key"
      ]
    },
    "CostCenter": {
      "tag_key": { "case_sensitive": false },
      "allowed_values": ["cc-1001", "cc-1002", "cc-1003", "cc-9999"],
      "enforced_for": [
        "ec2:instance",
        "s3:bucket",
        "lambda:function",
        "rds:db-instance"
      ]
    },
    "Owner": {
      "tag_key": {},
      "enforced_for": [
        "ec2:instance",
        "s3:bucket",
        "lambda:function"
      ]
    },
    "Project": {
      "tag_key": {},
      "enforced_for": ["ec2:instance", "s3:bucket"]
    }
  }
}
```

Create the policy:

```bash
aws organizations create-policy \
  --type TAG_POLICY \
  --name "baseline-tag-policy" \
  --description "Required tags with allowed_values enforcement" \
  --content file://tag-policy.json \
  --tags '[{"Key":"Governance","Value":"tag-baseline"}]'
```

Attach to root or OU:

```bash
aws organizations attach-policy \
  --policy-id p-xxxxxxx \
  --target-id r-xxxx      # root
  # --target-id ou-xxxx-xxxx   # OU
```

Verify enforcement:

```bash
# This call should FAIL if the tag value is not in allowed_values
aws ec2 create-tags \
  --resources i-0abc123 \
  --tags Key=Environment,Value=production
# AccessDenied / TagPolicyViolation — "production" not in allowed_values
```

**Common errors and fixes:**

| Error | Cause | Fix |
|---|---|---|
| `TagPolicyViolationException` on CreateTags | Tag value not in `allowed_values` | Use an allowed value, or extend `allowed_values` in the policy |
| Policy attached but no enforcement | `enforced_for` missing or typo'd resource type | Verify notation `service:resource-type` (lowercase) |
| Cannot add `staging` at OU level | Child policy is additive, cannot extend parent's `allowed_values` | Edit the root policy to include `staging` |
| `PolicyTypeNotEnabledException` | Tag policies not enabled at root | Run `enable-policy-type --policy-type TAG_POLICY` first |

### Step 3: Build EventBridge + Lambda auto-tagging

Auto-tagging stamps tags on resource creation so the fleet starts
compliant rather than waiting for remediation. The pattern: CloudTrail
logs the creation API call → EventBridge rule matches → Lambda derives
tags from the event context → Lambda calls the resource-type-specific
tagging API.

EventBridge rule for EC2 RunInstances:

```bash
aws events put-rule \
  --name auto-tag-ec2-on-create \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["ec2.amazonaws.com"],
      "eventName": ["RunInstances"]
    }
  }'
```

EventBridge rule for S3 CreateBucket and Lambda CreateFunction:

```bash
aws events put-rule \
  --name auto-tag-on-create-multi \
  --event-pattern '{
    "source": ["aws.s3", "aws.lambda"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["s3.amazonaws.com", "lambda.amazonaws.com"],
      "eventName": ["CreateBucket", "CreateFunction20150331"]
    }
  }'
```

Lambda handler (Python, handles EC2 + S3 + Lambda):

```python
import boto3, os, json

EC2 = boto3.client("ec2")
S3 = boto3.client("s3")
LAMBDA = boto3.client("lambda")

# Account ID -> Environment mapping (inject via env or Secrets Manager)
ACCOUNT_ENV = json.loads(os.environ["ACCOUNT_ENV_MAP"])

def lambda_handler(event, context):
    detail = event["detail"]
    source = detail["eventSource"]
    event_name = detail["eventName"]
    identity = detail["userIdentity"]
    user_arn = identity.get("arn", "unknown")
    user_name = user_arn.split("/")[-1] if "/" in user_arn else user_arn
    account_id = detail.get("recipientAccountId", event["account"])
    env = ACCOUNT_ENV.get(account_id, "unknown")
    base_tags = [
        {"Key": "Owner", "Value": user_name},
        {"Key": "CreatorARN", "Value": user_arn},
        {"Key": "Environment", "Value": env},
        {"Key": "CreatedVia", "Value": "auto-tagger"},
        {"Key": "CreatedAt", "Value": detail["eventTime"]},
    ]
    if source == "ec2.amazonaws.com" and event_name == "RunInstances":
        instances = detail["responseElements"]["instancesSet"]["items"]
        ids = [i["instanceId"] for i in instances]
        EC2.create_tags(Resources=ids, Tags=base_tags)
    elif source == "s3.amazonaws.com" and event_name == "CreateBucket":
        bucket = detail["requestParameters"]["bucketName"]
        S3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": base_tags})
    elif source == "lambda.amazonaws.com":
        fn = detail["requestParameters"]["functionName"]
        LAMBDA.tag_resource(Resource=fn, Tags={t["Key"]: t["Value"] for t in base_tags})
    return {"statusCode": 200, "tagged": True}
```

**Lambda execution role requirements:**
- `ec2:CreateTags` on `arn:aws:ec2:*:*:instance/*`
- `s3:PutBucketTagging` on `arn:aws:s3:::*`
- `lambda:TagResource` on `arn:aws:lambda:*:*:function:*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Trade-off table:**

| Dimension | EventBridge + Lambda | SSM Automation |
|---|---|---|
| Latency | ~seconds | ~minutes |
| Multi-resource type support | Custom branching logic | One document per type |
| Idempotency | Consumer must handle | SSM handles retries |
| Backfill (existing resources) | No — only creation events | Yes — Config-driven remediation |
| Audit trail | CloudTrail + Lambda logs | SSM execution history |

### Step 4: Resource Groups Tagging API bulk operations

For bulk tagging / untagging / inventory across resource types and
regions. The Tagging API normalizes the tagging interface across 30+
AWS services.

Bulk tag resources:

```bash
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    "arn:aws:ec2:us-east-1:111111111111:instance/i-0abc" \
    "arn:aws:s3:::my-bucket" \
    "arn:aws:lambda:us-east-1:111111111111:function:my-fn" \
  --tags Owner=platform-team,Environment=prod,CostCenter=cc-1001
# Returns: { "FailedResourcesMap": {} } on success
```

Bulk untag:

```bash
aws resourcegroupstaggingapi untag-resources \
  --resource-arn-list "arn:aws:s3:::my-bucket" \
  --tag-keys Owner Environment
```

Find resources by tag (multi-region iteration):

```bash
for region in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  aws resourcegroupstaggingapi get-resources \
    --tag-filters Key=Environment,Values=["prod"] \
    --resources-per-page 100 \
    --region "$region"
done > all-prod-resources.jsonl
```

List all tag keys and values in an account:

```bash
aws resourcegroupstaggingapi get-tag-keys
aws resourcegroupstaggingapi get-tag-values --key Environment
```

**Critical:** always check `FailedResourcesMap` in the response. A
non-empty map means some resources were not tagged (permission,
throttling, non-existent ARN). Log and retry the failed ARNs.

### Step 5: Wire Config `required-tags` managed rule

The Config managed rule `required-tags` checks that specified tag keys
exist on resources. It is the enforcement complement to the advisory
tag policy.

Deploy a required-tags rule via CLI:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-core",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "REQUIRED_TAGS"
    },
    "Scope": {
      "ComplianceResourceTypes": [
        "AWS::EC2::Instance",
        "AWS::S3::Bucket",
        "AWS::Lambda::Function",
        "AWS::RDS::DBInstance"
      ]
    },
    "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"
  }'
```

If you need more than 5 keys, deploy a second rule:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "required-tags-ext",
    "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance", "AWS::S3::Bucket"]},
    "InputParameters": "{\"tag1Key\":\"Backup:Required\",\"tag2Key\":\"ComplianceTier\",\"tag3Key\":\"DataClassification\"}"
  }'
```

Verify:

```bash
aws configservice describe-config-rules \
  --config-rule-names required-tags-core required-tags-ext

aws configservice get-compliance-details-by-config-rule \
  --config-rule-name required-tags-core \
  --compliance-types NON_COMPLIANT --limit 10
```

### Step 6: Security Hub integration

Tag compliance findings flow into Security Hub via the Config →
Security Hub integration pipe. The relevant control in Foundational
Security Best Practices (FSBP) is `[EC2.26]`, `[S3.10]`, `[Lambda.3]`
and similar — each checks for required tags on the resource type.

Enable Security Hub with FSBP:

```bash
aws securityhub enable-security-hub \
  --enable-default-standards
```

Verify the tag-related controls are active:

```bash
aws securityhub describe-standards-controls \
  --standards-subscription-arn arn:aws:securityhub:us-east-1:111111111111:standards/aws-foundational-security-best-practices/v/1.0.0 \
  --query 'Controls[?contains(ControlId, `Tag`)]'
```

For custom tag-compliance findings (beyond FSBP), import a finding
directly:

```bash
aws securityhub batch-import-findings \
  --findings '[{
    "SchemaVersion": "2018-10-08",
    "Id": "tag-violation/i-0abc123",
    "ProductArn": "arn:aws:securityhub:us-east-1:111111111111:product/111111111111/default",
    "GeneratorId": "custom-tag-checker",
    "AwsAccountId": "111111111111",
    "Types": ["Software and Configuration Checks/AWS Security Best Practices"],
    "CreatedAt": "2026-01-01T00:00:00Z",
    "UpdatedAt": "2026-01-01T00:00:00Z",
    "Severity": {"Label": "MEDIUM"},
    "Title": "Missing required tag: CostCenter",
    "Description": "EC2 instance i-0abc123 is missing the CostCenter tag.",
    "Resources": [{
      "Type": "AwsEc2Instance",
      "Id": "arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123",
      "Region": "us-east-1",
      "Tags": {"Environment": "prod"}
    }]
  }]'
```

### Step 7: Automated remediation (Config → SSM → Config re-evaluate)

When Config detects a missing required tag, wire a remediation that
adds a default or derived tag value, then Config re-evaluates and the
resource flips to COMPLIANT.

**Pattern A — SSM Automation document (custom, per resource type):**

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Add missing required tags to an EC2 instance'
parameters:
  InstanceId:
    type: String
    description: 'Injected by Config via RESOURCE_ID'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: CheckCurrentTags
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeTags
      Filters:
        - Name: resource-id
          Values: ['{{ InstanceId }}']
    outputs:
      - Name: ExistingKeys
        Selector: '$.Tags[].Key'
        Type: StringList
  - name: ApplyDefaultTags
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: CreateTags
      Resources: ['{{ InstanceId }}']
      Tags:
        - {Key: Environment, Value: unknown}
        - {Key: Owner, Value: platform-team}
        - {Key: Project, Value: unassigned}
        - {Key: CostCenter, Value: cc-9999}
    isCritical: true
    onFailure: abort
```

Wire remediation (default tags are placeholders — human review required
to set correct values):

```bash
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "required-tags-core",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "Custom-AddRequiredTagsEC2",
    "Automatic": false,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 600,
    "Parameters": {
      "InstanceId": {"ResourceValue": {"Value": "RESOURCE_ID"}},
      "AutomationAssumeRole": {"StaticValue": {"Values": ["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}
    }
  }]'
```

**Pattern B — EventBridge → Lambda (more flexible, branch by type):**

```bash
aws events put-rule \
  --name config-required-tags-noncompliant \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Rules Compliance Changed"],
    "detail": {
      "newEvaluationResult": {"complianceType": ["NON_COMPLIANT"]},
      "configRuleName": ["required-tags-core"]
    }
  }'
```

Lambda reads the resource, derives a best-guess tag (account → Environment,
creator from CloudTrail), and tags the resource. Idempotency is
critical — the same resource may emit NON_COMPLIANT multiple times.

**Critical:** remediation that stamps `Environment: unknown` is a
placeholder, not a fix. The verdict is AUTOMATED for the workflow
pipeline but flag a secondary manual step to correct the placeholder
values. Do NOT set `Automatic: true` on placeholder remediations
without a downstream human-correction queue.

### Step 8: Activate cost allocation tags

Cost allocation tags do NOT appear in Cost Explorer or CUR until
activated. Two activation paths:

**Path A — API (preferred for automation):**

```bash
aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status \
    '[{"TagKey":"Environment","Status":"Active"},
      {"TagKey":"Owner","Status":"Active"},
      {"TagKey":"Project","Status":"Active"},
      {"TagKey":"CostCenter","Status":"Active"}]'
```

Verify:

```bash
aws ce list-cost-allocation-tags \
  --status Active
```

**Path B — Billing console (fallback):**

```
Billing console → Cost Allocation Tags → user-defined cost allocation tags
→ Activate each tag key.
```

**User-defined vs AWS-generated tags:**

| Tag source | Examples | Activation |
|---|---|---|
| User-defined | `Owner`, `Environment`, `Project` | Must be activated manually |
| AWS-generated | `aws:createdBy`, `aws:cloudformation:stack-name` | `aws:createdBy` is auto-active; others must be activated |

**Org payer vs member accounts:** in a consolidated billing family,
activate tags on the payer account. The payer's cost allocation tag
settings apply to the consolidated CUR. Member-account-specific tags
require per-member activation for member-account-local reporting.

If the account does NOT support `ce update-cost-allocation-tags-status`
(legacy accounts or restricted IAM), the activation is a MANUAL step.
Flag `MANUAL_STEP_REQUIRED` with the Billing-console path.

### Step 9: ABAC IAM policy design

Attribute-based access control uses resource and principal tags in IAM
condition keys to make access decisions. ABAC scales better than RBAC
for large orgs because new resources and principals inherit access from
their tags — no policy edit needed.

**ABAC condition keys:**

| Condition key | Source | When evaluated |
|---|---|---|
| `aws:ResourceTag/<key>` | Resource tags | On every API call against the resource |
| `aws:PrincipalTag/<key>` | IAM user/role session tags | At session creation (fixed for session lifetime) |
| `aws:RequestTag/<key>` | Tags in the API request | On create / tag operations only |
| `aws:TagKeys` | List of tag keys in request | On tag operations |

**ABAC policy pattern (team-scoped S3 access):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::team-data-*/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Team": "${aws:PrincipalTag/Team}"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "s3:CreateBucket",
      "Resource": "arn:aws:s3:::*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Team": "${aws:PrincipalTag/Team}"
        },
        "ForAllValues:StringEquals": {
          "aws:TagKeys": ["Team", "Environment", "Owner"]
        }
      }
    }
  ]
}
```

**ABAC prerequisites checklist:**
1. IAM principals (users / roles) are tagged with the attribute (e.g., `Team`).
2. Resources are tagged with the same attribute.
3. The IAM policy uses `aws:ResourceTag` matching `aws:PrincipalTag`.
4. The tag policy (Step 2) enforces that the attribute tag key exists on
   new resources (otherwise ABAC silently breaks for new resources).
5. Session tags are passed on `AssumeRole` via `--tags` or STS session
   tagging.

**Common ABAC pitfall:** `StringEquals` is case-sensitive. If your tag
policy allows `case_sensitive: false` for `Environment`, but your IAM
condition is `StringEquals: {"aws:ResourceTag/Environment": "prod"}`,
a resource tagged `Prod` fails the check. Either enforce
`case_sensitive: true` in the tag policy OR use
`StringEqualsIgnoreCase` in the IAM condition.

### Step 10: Audit and verify a deployed governance baseline

End-to-end verification of the tag governance stack:

```bash
# 1. Tag policy is attached and enforced
aws organizations list-policies --filter TAG_POLICY \
  --query 'Policies[].{Name:Name,Id:Id,State:AwsManaged}'
aws organizations describe-policy --policy-id p-xxxxxxx

# 2. Config required-tags rule is evaluating
aws configservice describe-config-rules \
  --config-rule-names required-tags-core
aws configservice get-compliance-summary-by-config-rule

# 3. Auto-tagger Lambda is firing
aws logs filter-log-events \
  --log-group-name /aws/lambda/auto-tagger \
  --filter-pattern '"tagged": true' \
  --start-time $(date -d '1 hour ago' +%s)000

# 4. Security Hub has the tag findings
aws securityhub get-findings \
  --filters '{"GeneratorId":[{"Value":"required-tags","Comparison":"CONTAINS"}]}' \
  --query 'Findings[].{Id:Id,Severity:Severity.Label,Title:Title}'

# 5. Cost allocation tags are active
aws ce list-cost-allocation-tags --status Active

# 6. Resource tag coverage (sample)
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=["prod"] \
  --resources-per-page 50
```

A governance baseline that passes Steps 1-3 but has zero active cost
allocation tags (Step 5) is incomplete — cost reporting will show no
tag dimensions.

## STRICT output contract

Every output MUST follow this exact structure. Deviations are bugs in
the skill.

```text
GOVERNANCE: <reference>
SCOPE: <accounts / OUs / regions covered>
STRATEGY:
  - Required tags: <comma-separated keys>
  - Optional tags: <comma-separated keys or "none">
  - Enforcement layer: <Organizations TagPolicy | Config rule | both>
POLICY:
  - Type: <Organizations TagPolicy | Config required-tags | EventBridge auto-tagger | ABAC IAM | conformance pack>
  - Attached to: <root | OU | account | resource>
  - Template: <inline JSON/YAML or "see Step N">
AUTOMATION:
  - Auto-tagging: <EventBridge + Lambda | none>
  - Remediation: <SSM Automation | Lambda | none>
  - Trigger: <automatic | manual>
COMPLIANCE:
  - Detection: <Config rule name(s)>
  - Reporting: <Security Hub | Config dashboard | both>
  - Cost allocation: <active | inactive | pending>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <full CLI snippet or policy JSON>
```

### Worked example — AUTOMATED, full tag governance baseline

```text
GOVERNANCE: org-tag-baseline
SCOPE: org root r-xxxx, all member accounts, us-east-1 + us-west-2
STRATEGY:
  - Required tags: Environment, Owner, Project, CostCenter, Application
  - Optional tags: Backup:Required, ComplianceTier, DataClassification
  - Enforcement layer: Organizations TagPolicy + Config required-tags rule
POLICY:
  - Type: Organizations TagPolicy + Config required-tags-core
  - Attached to: root (policy), Config recorder (rule)
  - Template: see Step 2 (TagPolicy JSON) + Step 5 (Config rule)
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances, CreateBucket, CreateFunction
  - Remediation: SSM Automation Custom-AddRequiredTagsEC2 (manual trigger, placeholder values)
  - Trigger: manual (placeholder remediation requires human correction)
COMPLIANCE:
  - Detection: required-tags-core, required-tags-ext
  - Reporting: Security Hub FSBP controls + Config compliance dashboard
  - Cost allocation: active (Environment, Owner, Project, CostCenter via ce API)
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws organizations create-policy --type TAG_POLICY --name baseline-tag-policy --content file://tag-policy.json
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"required-tags-core","Source":{"Owner":"AWS","SourceIdentifier":"REQUIRED_TAGS"},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance","AWS::S3::Bucket","AWS::Lambda::Function","AWS::RDS::DBInstance"]},"InputParameters":"{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"}'
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[{"TagKey":"Environment","Status":"Active"},{"TagKey":"Owner","Status":"Active"},{"TagKey":"Project","Status":"Active"},{"TagKey":"CostCenter","Status":"Active"}]'
```

### Worked example — MANUAL_STEP_REQUIRED, cost allocation activation on legacy account

```text
GOVERNANCE: legacy-account-cost-tags
SCOPE: account 222222222222 (legacy, pre-2020)
STRATEGY:
  - Required tags: Environment, Owner, CostCenter
  - Optional tags: none
  - Enforcement layer: Config required-tags (already deployed)
POLICY:
  - Type: Cost allocation tag activation
  - Attached to: payer account 222222222222
  - Template: N/A — manual console step required
AUTOMATION:
  - Auto-tagging: N/A (already deployed via EventBridge)
  - Remediation: N/A
  - Trigger: N/A
COMPLIANCE:
  - Detection: required-tags-core (already firing)
  - Reporting: Config dashboard only (no Cost Explorer dimension — tags inactive)
  - Cost allocation: INACTIVE — cannot activate via API on this account
VERDICT: MANUAL_STEP_REQUIRED
GAP: Account 222222222222 does not support ce update-cost-allocation-tags-status (IAM policy restriction on payer). Manual step required: Billing console -> Cost Allocation Tags -> activate Environment, Owner, CostCenter. Propagation takes up to 24 hours.
TEMPLATE: (manual console step — no API path available for this account)
```

## Anti-Patterns — NEVER do these things

- NEVER publish a TagPolicy without `enforced_for`. The policy with
  `allowed_values` but no `enforced_for` is advisory — AWS does not
  block non-compliant operations. Operators assume enforcement and
  drift accumulates silently.

- NEVER assume tag policy child policies can override the parent. They
  cannot. Child OU and account policies are additive (union). To relax
  a parent's `allowed_values`, edit the parent. A common mistake is
  attaching a child policy with `allowed_values: ["staging"]` and
  assuming it merges with the parent's `["dev", "prod"]` — it does
  not. The child can only further restrict.

- NEVER use `StringEquals` for ABAC conditions when the tag policy has
  `case_sensitive: false`. The case-insensitive tag policy allows
  `Prod` and `prod`; the IAM condition matches only `prod`. This
  produces silent under-grants (legitimate access denied) OR
  over-grants (a `Deny` with `StringNotEquals` silently passes). Use
  `StringEqualsIgnoreCase` for ABAC conditions OR enforce
  `case_sensitive: true` in the tag policy.

- NEVER assume cost allocation tags are active by default. They are
  NOT. A fully tagged fleet with zero activated tag keys produces
  zero cost-dimension data in Cost Explorer and CUR. Always verify
  with `ce list-cost-allocation-tags --status Active`.

- NEVER deploy a single Config `required-tags` rule for more than 5
  tag keys. The managed rule silently ignores keys beyond the 5th
  (`tag6Key`...`tag7Key` are not accepted parameters). Deploy multiple
  required-tags rules (e.g., `required-tags-core`, `required-tags-ext`).

- NEVER assume `resourcegroupstaggingapi get-resources` returns global
  results. It is region-scoped. Querying only `us-east-1` misses
  resources in other regions. Iterate over all enabled regions.

- NEVER ignore `FailedResourcesMap` in a `tag-resources` response. A
  non-empty map means some resources were not tagged. The API call
  "succeeded" but the tagging is partial. Log, retry, and alert on
  persistent failures.

- NEVER wire auto-tagging without a tag policy. The Lambda stamps
  tags on creation, but nothing stops a human from modifying them
  afterward. Pair auto-tagging with a TagPolicy that enforces
  `allowed_values` on the same keys.

- NEVER set `Automatic: true` on placeholder-tag remediation (e.g.,
  `Environment: unknown`) without a downstream human-correction queue.
  The placeholder satisfies the Config rule but pollutes ABAC and
  cost reporting. Always flag placeholder remediation as a secondary
  manual step.

- NEVER use `aws:RequestTag` in a policy governing read operations
  (`s3:GetObject`, `ec2:DescribeInstances`). `aws:RequestTag` is only
  present on create / tag API calls. A `Deny` with `aws:RequestTag`
  on a read operation silently never matches.

- NEVER assume IAM principal tags propagate to existing sessions.
  `aws:PrincipalTag` is resolved at session creation. Changing a
  user's `Team` tag does not affect active sessions until they
  re-authenticate. Coordinate tag changes with session refresh.

- NEVER forget that Organizations TagPolicy does NOT enforce on
  AWS-generated tags (`aws:cloudformation:stack-name`,
  `aws:createdBy`). These are system tags. User-defined policies apply
  only to user-supplied keys. If your ABAC depends on `aws:createdBy`,
  there is no enforcement lever — it is always present but read-only.

- NEVER deploy ABAC without tagging the IAM principals first. An ABAC
  policy using `aws:PrincipalTag/Team` on an untagged role silently
  denies all access (empty string does not match). Verify principal
  tags with `iam list-user-tags` / `list-role-tags` before deploying
  the policy.

- NEVER bulk-tag resources across accounts without assuming a role in
  each target account. The Tagging API operates within the caller's
  account. A cross-account bulk-tag script requires `sts:AssumeRole`
  into each member account.

## Pre-flight safety checks (run before applying any tag governance CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-policy`, `attach-policy`, `put-config-rule`,
  `put-remediation-configurations`, `tag-resources` bulk), emit:
  `CONFIRM: About to <action> for scope <scope>. This affects
  <consequence>. Proceed? (yes/no)`

- **Back up the existing tag policy** before modifying:
  `aws organizations describe-policy --policy-id p-xxxxxxx > /tmp/tag-policy-backup-$(date +%s).json`
  Tag policies have no version history.

- **Test the tag policy in a sandbox OU first.** Attach to a
  non-production OU, create a test resource with a non-compliant tag,
  verify the `CreateTags` call is blocked, then promote to root.

- **Before activating cost allocation tags**, verify the payer account
  supports `ce update-cost-allocation-tags-status`. Legacy accounts or
  accounts with restricted IAM may require the Billing console path.

- **Before deploying ABAC**, inventory principal tags:
  `aws iam list-user-tags --user-name <name>`. An ABAC policy on
  untagged principals is a guaranteed access outage.

## Appendix A — Canonical tag key reference

| Tag key | Type | Required? | Common allowed values | Consumers |
|---|---|---|---|---|
| `Environment` | Required | Yes | `dev`, `staging`, `prod` | ABAC, Cost Explorer, Config scoping |
| `Owner` | Required | Yes | email / team alias | Accountability, alert routing |
| `Project` | Required | Yes | project code | Cost allocation |
| `CostCenter` | Required | Yes | `cc-NNNN` | Finance reporting |
| `Application` | Required | Yes | app name | Dependency mapping |
| `Team` | Required (ABAC) | If ABAC | team name | ABAC `aws:PrincipalTag/Team` |
| `Backup:Required` | Optional | No | `true`, `false` | Backup policy routing |
| `ComplianceTier` | Optional | No | `tier-1`, `tier-2`, `tier-3` | Audit cadence |
| `DataClassification` | Optional | No | `public`, `internal`, `confidential` | Macie, KMS routing |
| `CreatedAt` | Auto | No | ISO timestamp (auto-tagger) | Age-based cleanup |
| `CreatorARN` | Auto | No | IAM ARN (auto-tagger) | Audit trail |
| `CreatedVia` | Auto | No | `auto-tagger`, `console`, `terraform` | Provisioning source |

## Appendix B — Decision tree (which enforcement layer)

```
Is the requirement to PREVENT non-compliant tags at creation?
├─ Yes → Organizations TagPolicy with enforced_for (Step 2)
│         (blocks the API call; does not fix existing resources)
│
└─ No → Is the requirement to DETECT and REPORT missing tags?
        ├─ Yes → Config required-tags rule (Step 5) + Security Hub (Step 6)
        │
        └─ No → Is the requirement to AUTO-STAMP tags on creation?
                ├─ Yes → EventBridge + Lambda auto-tagger (Step 3)
                │
                └─ No → Is the requirement to REMEDIATE existing untagged resources?
                        ├─ Yes → Config → SSM Automation / Lambda remediation (Step 7)
                        │
                        └─ No → Is the requirement to USE tags for access decisions?
                                ├─ Yes → ABAC IAM policy (Step 9)
                                │
                                └─ No → Is the requirement for COST REPORTING?
                                        ├─ Yes → Cost allocation tag activation (Step 8)
                                        │
                                        └─ Default: tag strategy framework (Step 1)
```

## Recent AWS features (2024-2026)

- **Organizations TagPolicy ABAC support (2024-2025):** Tag policies
  now integrate directly with ABAC patterns via `aws:ResourceTag`
  conditions. A tag policy that enforces `Team` on resources combined
  with an IAM policy using `aws:ResourceTag/Team` =
  `${aws:PrincipalTag/Team}` gives org-wide team-scoped access without
  per-team policies.

- **`ce update-cost-allocation-tags-status` GA (2023-2024):**
  Programmatic activation of cost allocation tags — previously
  Billing-console-only. The API enables org-wide automated activation
  via a script iterating member accounts. Legacy accounts may still
  require the console path.

- **Resource Groups Tagging API `get-resources` pagination improvements
  (2024):** Higher `--resources-per-page` limits and faster
  cross-region aggregation. Multi-region tag inventory is now practical
  for fleets of 100k+ resources.

- **Config required-tags multi-rule support (2024):** Multiple
  `required-tags` rules per account are now fully supported without
  evaluation conflicts. Previously, overlapping scopes produced
  inconsistent compliance states.

- **Security Hub custom findings for tag violations (2024-2025):**
  `batch-import-findings` now accepts custom tag-compliance findings
  with `AwsAccountId` + `Resources[].Tags`, enabling integration with
  third-party tag governance tools (not just Config-managed rules).

- **EventBridge cross-account event routing for auto-tagging (2024):**
  A single auto-tagger Lambda in the org management account can now
  receive CloudTrail events from member accounts via EventBridge
  cross-account routing. Previously required per-account Lambda
  deployment.

- **IAM session tagging for ABAC (2024):** `sts:AssumeRole` with
  `--tags` and `--transitive-tag-keys` allows ABAC across role chains.
  Session tags propagate through the AssumeRole chain, enabling
  team-scoped cross-account access without long-lived principal tags.

## Expert heuristic: tag governance blast radius

Tag governance changes are deceptively high-risk. A single misconfigured
TagPolicy attached to the org root can block ALL `CreateTags` calls
across the entire organization — including infrastructure-as-code
pipelines (Terraform, CloudFormation) that tag resources on creation.
The result is a fleet-wide provisioning outage within minutes.

**The rule (non-negotiable):**

> ALWAYS test tag policies in a sandbox OU first. Attach the policy to
> a non-production OU, verify enforcement on 3+ resource types, then
> promote to root. NEVER attach an untested TagPolicy to the org root
> on first contact.

**Why this rule exists:** the TagPolicy `enforced_for` list blocks
API calls. If the `allowed_values` are wrong (a typo, a missing valid
value), every `CreateTags` call with the "wrong" value fails. Terraform
apply fails. CloudFormation stack create fails. Auto-scaling launches
fail (if the launch template tags the instance). The blast radius is
the entire OU tree.

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| Sandbox OU attachment | Attach policy to `ou-sandbox` only | Zero production exposure |
| Single resource type | `enforced_for: ["ec2:instance"]` only | Limits to one service |
| `allowed_values` with wildcard | Include `*` as a temporary allowed value during rollout | Allows all values; enforcement is on key presence only |
| Config rule before TagPolicy | Deploy Config `required-tags` first (detect only) | Detect + report without blocking API calls |
| Dry-run via CloudTrail replay | Replay recent CloudTrail `CreateTags` events against the policy offline | Identifies what would have been blocked |

**Pre-production validation protocol (3-phase rollout):**

1. **Phase 1 — DETECT (Config only):** Deploy Config `required-tags`
   rules. Monitor NON_COMPLIANT counts for 1 week. Identify resources
   that would be affected. Do NOT deploy the TagPolicy yet.
2. **Phase 2 — ENFORCE (sandbox OU):** Attach the TagPolicy to a
   sandbox OU. Create test resources with compliant and non-compliant
   tags. Verify the API blocks the non-compliant call. Fix any
   false-positive blocks.
3. **Phase 3 — ENFORCE (root):** Promote the TagPolicy to the org
   root. Monitor CloudTrail for `TagPolicyViolationException` spikes.
   Have a rollback plan (`detach-policy`) ready.

**Cost allocation tag activation blast radius:** activating a tag key
in Billing does NOT affect resource operations — it only controls
whether the tag appears as a dimension in Cost Explorer / CUR. The
risk is reporting-only (a misnamed tag key produces a useless
dimension). Always verify tag key spelling against the actual resource
tags (`resourcegroupstaggingapi get-tag-keys`) before activating.

**ABAC blast radius:** an ABAC policy that uses `aws:PrincipalTag/Team`
on an untagged role produces an immediate access outage for every
session of that role. Always verify principal tags before deploying
the policy. Deploy in `Audit` mode first (use `aws:PrincipalTag/Team`
in a `Deny` with `StringNotEquals` to LOG violations via CloudTrail
before enforcing).

**Surface in the output:** for any recommended tag governance change,
include `BLAST_RADIUS: <scope>` (e.g., `org-root`,
`sandbox-ou-scoped`, `single-account`) and `VALIDATION_PHASE:
<detect | sandbox-enforce | root-enforce>`. If `VALIDATION_PHASE` is
not `root-enforce`, do NOT mark the recommendation as production-ready.

## Domain

AWS CloudOps / Governance Automation — Tag governance, ABAC, cost
allocation.

## AWS documentation

- **Organizations Tag Policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html
- **Resource Groups Tagging API** — https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/overview.html
- **AWS Config required-tags Rule** — https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html
- **ABAC for AWS** — https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction_attribute-based-access-control.html
- **Cost Allocation Tags** — https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html
- **Security Hub Foundational Security Best Practices** — https://docs.aws.amazon.com/securityhub/latest/userguide/fsbp-standard.html
