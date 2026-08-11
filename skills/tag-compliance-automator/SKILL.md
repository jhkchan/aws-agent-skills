---
name: tag-compliance-automator
description: >-
  Automates AWS tag compliance end-to-end: Organizations tag policies
  with case-sensitive key/value validation and enforced_for scoping,
  Resource Groups Tagging API bulk operations, Config managed rules
  (required-tags, allowed-tag-values) plus custom Lambda rules for 6+
  keys, EventBridge + Lambda auto-tagging on EC2/S3/Lambda creation
  with inherited-tag propagation (EC2 to EBS and ENIs), tag drift
  detection via Config CI change events, remediation via SSM Automation,
  cost allocation tag activation via Cost Explorer API, and cross-account
  consistency via CloudFormation StackSets. Emits AUTOMATION_DEPLOYED
  with deployment templates or REVIEW_REQUIRED with the specific gap.
  Use when building tag compliance automation, enforcing a tag schema,
  wiring auto-tagging, or remediating tag drift across an organization.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline policy design. Live deployment
  uses aws organizations enable-policy-type, create-policy, update-policy,
  attach-policy, aws resourcegroupstaggingapi tag-resources, untag-resources,
  get-resources, aws configservice put-config-rule, put-remediation-configurations,
  aws ce update-cost-allocation-tags-status, aws ssm create-document,
  start-automation-execution, aws lambda create-function, aws events put-rule,
  put-targets, and aws cloudformation create-stack-set — AWS CLI v2, SSO or
  key-based credentials, Organizations management or delegated-administrator
  permissions.
keywords:
  - AWS Organizations
  - Tag Policy
  - TagPolicy
  - case_sensitive
  - enforced_for
  - allowed_values
  - Resource Groups Tagging API
  - tag-resources
  - untag-resources
  - get-resources
  - AWS Config
  - required-tags
  - allowed-tag-values
  - tag drift
  - EventBridge
  - Lambda auto-tagging
  - tag propagation
  - EC2 EBS ENI
  - cost allocation tags
  - Cost Explorer API
  - CloudFormation StackSets
  - SSM Automation
  - tag compliance
  - tag schema
  - Environment Owner CostCenter Project
tags: [aws-organizations, tag-policy, resource-groups-tagging-api, aws-config, eventbridge, lambda, cost-explorer, cloudformation-stacksets, ssm-automation, automate]
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
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Designing Organizations tag policies with case-sensitive key/value
    validation, building EventBridge + Lambda auto-tagging pipelines with
    inherited-tag propagation (EC2 to EBS/ENI), running Resource Groups
    Tagging API bulk operations, wiring Config required-tags and
    allowed-tag-values rules with drift detection, remediating tag drift
    via SSM Automation, activating cost allocation tags programmatically,
    or enforcing cross-account tag consistency via CloudFormation StackSets.
  activation_triggers:
    - "tag compliance automation"
    - "Organizations tag policy case_sensitive"
    - "auto-tag on creation EventBridge Lambda"
    - "tag propagation EC2 EBS ENI"
    - "Resource Groups Tagging API bulk"
    - "tag-resources untag-resources get-resources"
    - "required-tags allowed-tag-values Config rule"
    - "tag drift detection remediation"
    - "cost allocation tag activation"
    - "cross-account tag consistency StackSets"
    - "tag schema enforcement"
    - "Environment Owner CostCenter Project tags"
  invocation_schema: >-
    Input: either (a) a tag compliance requirement ("enforce Environment,
    Owner, CostCenter, Project tags on all EC2, S3, and RDS resources with
    auto-tagging and drift remediation", "propagate tags from EC2 to EBS
    volumes and ENIs on creation", "activate cost allocation tags
    programmatically"), OR (b) an existing tag policy, Config rule, or
    EventBridge auto-tagger to audit and harden. Output: deterministic
    COMPLIANCE block per requirement — POLICY/DETECTION/AUTOMATION/
    PROPAGATION/REMEDIATION/COST/VERDICT — where VERDICT is
    AUTOMATION_DEPLOYED (templates ready and validated) or REVIEW_REQUIRED
    (specific gap cited, e.g., manual Billing-console step or untested
    custom runbook).
---

# Tag Compliance Automator

## Mindset

**One-line takeaway:** tag compliance is a four-layer pipeline —
**define** (Organizations TagPolicy sets case-sensitive key/value rules
with `enforced_for` scoping) → **detect** (Config `required-tags` and
`allowed-tag-values` rules flag non-compliant resources; Config
configuration-item changes catch tag drift) → **propagate** (EventBridge
+ Lambda auto-tags new resources on creation and propagates inherited
tags from EC2 to child EBS volumes and ENIs) → **remediate** (SSM
Automation or Lambda adds or corrects missing tags; Config re-evaluates
and flips COMPLIANT). A gap in ANY layer produces a silent failure: the
policy is published but advisory, auto-tagging stamps tags that humans
later overwrite, drift goes undetected, or cost allocation reports stay
empty because no one activated the tag keys in Billing.

- **Organizations TagPolicy** without `enforced_for` is advisory only:
  the policy declares that `Environment` must be `dev`, `staging`, or
  `prod`, but if no resource type is listed under `enforced_for`, AWS
  does not block non-compliant tag operations on those resources. The
  policy is documentation, not enforcement.
- **Case sensitivity** is a silent gap. A TagPolicy with
  `case_sensitive: true` treats `Environment` and `environment` as
  different keys. A Config rule checking for `Environment` does not flag
  a resource tagged `environment=prod`. Auto-taggers that derive the key
  name from an EventBridge event detail must match the policy's casing
  exactly, or the tag is stamped but the resource still shows
  NON_COMPLIANT.
- **Tag propagation is NOT automatic.** When an operator launches an EC2
  instance with tags, the tags do NOT propagate to the EBS volumes or
  ENIs created in the same `RunInstances` call. The volumes and ENIs are
  untagged, which breaks cost allocation and ABAC. An EventBridge rule
  on `RunInstances` must invoke a Lambda that calls
  `ec2:create-tags` on the child resources.
- **Cost allocation tags are NOT active by default.** A perfectly tagged
  fleet produces zero cost-dimension data in CUR and Cost Explorer until
  an administrator activates the tag keys via the Billing API or console.
  This is the number-one "we tagged everything and Cost Explorer is still
  empty" issue.

## Quick navigation

| You want to... | Go to |
|---|---|
| Design an Organizations TagPolicy with case-sensitive enforcement | Step 1 + Appendix A |
| Pick between Config `required-tags` and a custom Lambda rule | Step 2 |
| Wire an EventBridge auto-tagger for new resources | Step 3 |
| Propagate tags from EC2 to EBS volumes and ENIs | Step 4 |
| Detect and remediate tag drift via Config | Step 5 + Step 6 |
| Bulk-tag existing resources via Resource Groups Tagging API | Step 7 |
| Activate cost allocation tags programmatically | Step 8 |
| Enforce cross-account tag consistency via StackSets | Step 9 |
| Avoid common tag-policy and propagation pitfalls | Anti-Patterns |
| Recent features (tag-policy enforced_for expansion, StackSets drift) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **`enforced_for` is the only enforcement hook in a TagPolicy.** A
   policy with `allowed_values` but no `enforced_for` entries is
   advisory — AWS does not block non-compliant operations. Always list
   the resource types under `enforced_for` for every tag key you want
   enforced.
2. **`case_sensitive` defaults to `true` and mismatches break
   silently.** If the policy declares `Environment` (capital E) and a
   resource is tagged `environment` (lowercase), the policy does NOT
   match the key. Config `required-tags` also checks the exact key name.
   Normalize casing in the auto-tagger before stamping.
3. **Config `required-tags` checks at most 5 tag keys per rule.** To
   enforce 6+ required keys, deploy a second rule (`required-tags-ext`)
   or a custom Lambda rule. The managed rule silently ignores keys
   beyond the 5th.
4. **EC2 tags do NOT propagate to EBS volumes or ENIs.** The
   `RunInstances` API tags only the instance. Child resources are
   untagged. An EventBridge-driven Lambda must call
   `ec2:create-tags` on `VolumeId` and `NetworkInterfaceId` values from
   the `RunInstances` response.
5. **Cost allocation tag activation is account-scoped and per-key.** The
   `ce update-cost-allocation-tags-status` API activates a tag key for
   the payer account only. Member-account tags roll up via the payer,
   but the key must be activated on the payer before it appears as a
   Cost Explorer dimension.

## Pre-flight: data requirements

Designing a tag compliance automation pipeline requires these inputs:

| Input | Source | Why |
|---|---|---|
| Existing tag policies | `organizations list-policies --filter TAG_POLICY` | Avoid overwriting an in-use policy |
| Organization root ID | `organizations list-roots` | Attachment target for the policy |
| Tag policy type enabled | `organizations describe-organization` `AvailablePolicyTypes` | Must enable TAG_POLICY before attaching |
| Config recorder status | `configservice describe-configuration-recorders` | Rules cannot evaluate without a recorder |
| Current cost allocation tag status | `ce list-cost-allocation-tags` | Avoid redundant activation calls |
| Sample resource tag coverage | `resourcegroupstaggingapi get-resources` | Baseline before enforcement |
| Existing EventBridge rules on EC2/S3 | `events list-rules` | Avoid duplicate auto-tagger rules |
| SSM service role ARN | `iam get-role` on the SSM automation role | Remediation execution identity |
| StackSet admin role | `cloudformation describe-stack-set` | Cross-account tag-policy deployment |

**If the input is malformed** (missing tag schema, ambiguous resource
type list), emit:

```text
COMPLIANCE: <reference>
VERDICT: ERROR
REASON: Cannot design tag compliance automation — tag schema and target resource types are required.
GAP: Re-supply the required tag keys, allowed values, and the resource types in scope.
```

## Process — Compliance automation design (apply in order)

### Step 0: Expert knowledge — non-obvious TagPolicy and Config behaviors

These behaviors change the design if ignored:

- **A TagPolicy attached to the org root cascades to all OUs and
  accounts, but a policy attached to a specific OU overrides (not
  merges) the root policy for accounts under that OU.** The effective
  tag policy for an account is the policy attached to the closest
  ancestor (root or OU). Merging is NOT the model. To add a key to a
  child OU without losing root keys, the child policy must re-declare
  every parent key.

- **`enforced_for` accepts resource types in the
  `AWS::service::resource` format (e.g., `AWS::EC2::Instance`).** A
  typo like `AWS::EC2::instance` (lowercase) is silently ignored. The
  enforcement does not fire. Always cross-reference the canonical
  resource-type list in the AWS documentation.

- **Config `required-tags` uses `InputParameters` as a JSON-encoded
  string, not a YAML map.** A common Terraform / CloudFormation failure
  is passing a map where the API expects `"{\"tag1Key\":\"Environment\"}"`.
  The rule deploys but never evaluates — the input is silently dropped.

- **The Resource Groups Tagging API `tag-resources` is eventually
  consistent for some services.** Tagging an S3 bucket returns
  `SUCCESS` immediately, but a follow-up `get-resources` within seconds
  may not reflect the new tags. For validation, sleep 10-15 seconds
  before re-querying.

- **EventBridge auto-taggers that derive Owner from the IAM principal
  must handle assumed-role sessions.** The `userIdentity.sessionContext`
  in the CloudTrail event has `sessionIssuer.arn` (the role) and
  `sessionContext.attributes.mfaAuthenticated`. Deriving a human owner
  from a role ARN requires a mapping table. Tagging the resource with
  the role ARN as Owner works for ABAC but produces noisy cost reports.

- **`allowed-tag-values` is a Config managed rule that checks a tag
  key's value against an allowlist.** It accepts one tag key per rule
  invocation. To validate 4 tag keys' values, deploy 4 separate
  `allowed-tag-values` rules. A single rule cannot validate multiple
  keys' values.

- **CloudFormation StackSets for tag policies require the
  `AWSCloudFormationStackSetAdministrationRole` and a per-target
  execution role.** A StackSet deploy without the execution role in a
  target account fails with `AccessDenied` on the target, not on the
  deployer. Pre-provision both roles via the StackSet admin template.

- **The `ce update-cost-allocation-tags-status` API has a propagation
  delay of up to 24 hours.** Activating a tag key returns immediately,
  but Cost Explorer and CUR do not reflect the new dimension until the
  next processing cycle. Do not re-activate or assume failure within
  that window.

- **Config configuration-item change events on tag updates fire for
  recorded resource types only.** A resource type not in the recorder's
  recording group does not emit configuration-item changes. Tag drift
  on such resources is invisible to Config. Extend the recorder scope
  before wiring drift detection.

### Step 1: Design the Organizations TagPolicy

The TagPolicy JSON declares, per tag key: `TagKey` (the key name),
`Targets` (optional: specific values that are allowed), and
`EnforcedFor` (the resource types that must comply). Wrap per-key
declarations under a `tags` object.

Tag policy JSON structure:

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
    "Owner": {
      "TagKey": "Owner",
      "EnforcedFor": [
        "AWS::EC2::Instance",
        "AWS::S3::Bucket",
        "AWS::RDS::DBInstance"
      ]
    },
    "CostCenter": {
      "TagKey": "CostCenter",
      "ExpectedStringValues": ["cc-100", "cc-200", "cc-300"],
      "EnforcedFor": ["AWS::EC2::Instance", "AWS::S3::Bucket"]
    },
    "Project": {
      "TagKey": "Project",
      "EnforcedFor": ["AWS::EC2::Instance", "AWS::Lambda::Function"]
    }
  }
}
```

CLI deployment:

```bash
aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICY

aws organizations create-policy \
  --type TAG_POLICY \
  --name baseline-compliance-tag-policy \
  --description "Enforced tag keys: Environment, Owner, CostCenter, Project" \
  --content file://tag-policy.json

aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx
```

Decision table — enforcement vs advisory:

| TagPolicy shape | Behavior | Verdict impact |
|---|---|---|
| `allowed_values` set, `enforced_for` empty | Advisory — no operation blocked | REVIEW_REQUIRED (enforcement gap) |
| `allowed_values` set, `enforced_for` populated | Enforced — non-compliant tag op returns `ConstraintViolation` | AUTOMATION_DEPLOYED |
| No `allowed_values`, `enforced_for` populated | Key presence enforced, value not validated | AUTOMATION_DEPLOYED (presence only) |
| `case_sensitive: false` declared | Case-insensitive match on key name | AUTOMATION_DEPLOYED (note: Config rules still match exact case) |

**Decision rule:** default to including `enforced_for` for every
production resource type. Advisory policies (no `enforced_for`) are
acceptable for a soft-launch phase but MUST be flagged
`REVIEW_REQUIRED` until enforcement is on.

### Step 2: Choose the Config rule pattern

| Pattern | Rule type | Use case | Limit |
|---|---|---|---|
| Required keys presence | `required-tags` (managed) | Enforce that N tag keys exist on a resource | Max 5 keys per rule |
| Allowed values per key | `allowed-tag-values` (managed) | Enforce that a tag key's value is in an allowlist | One key per rule |
| Custom multi-key validation | Custom Lambda rule | 6+ required keys, regex value matching, conditional logic | Lambda maintenance overhead |
| Tag drift detection | Custom Lambda on Config CI change | Detect tag removal or value change after creation | Requires recorder coverage of the resource type |

Deploy `required-tags` for the first 5 keys:

```bash
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "required-tags-core",
  "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
  "Scope": {
    "ComplianceResourceTypes": [
      "AWS::EC2::Instance",
      "AWS::S3::Bucket",
      "AWS::RDS::DBInstance",
      "AWS::Lambda::Function"
    ]
  },
  "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"
}'
```

Deploy `allowed-tag-values` for the Environment key:

```bash
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "allowed-tag-values-environment",
  "Source": {"Owner": "AWS", "SourceIdentifier": "ALLOWED_TAG_VALUES"},
  "Scope": {
    "ComplianceResourceTypes": ["AWS::EC2::Instance", "AWS::S3::Bucket"]
  },
  "InputParameters": "{\"tagKey\":\"Environment\",\"values\":[\"dev\",\"staging\",\"prod\"]}"
}'
```

For the 6th+ required key or conditional logic, deploy a custom Lambda
rule. The rule's evaluation payload includes the resource's tags; the
Lambda returns `COMPLIANT` or `NON_COMPLIANT` with an annotation.

### Step 3: Wire the EventBridge auto-tagger

The auto-tagger fires on resource-creation events and stamps inherited
or derived tags. It must be idempotent (a replayed event must not error
on duplicate tags) and case-normalized (keys must match the TagPolicy
exactly).

EventBridge rule for EC2, S3, Lambda creation:

```bash
aws events put-rule --name auto-tag-on-create --event-pattern '{
  "source": ["aws.ec2", "aws.s3", "aws.lambda"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com", "s3.amazonaws.com", "lambda.amazonaws.com"],
    "eventName": ["RunInstances", "CreateBucket", "CreateFunction20150331"]
  }
}'
```

Lambda handler sketch (Python):

```python
import boto3, os, json

ec2 = boto3.client("ec2")
s3 = boto3.client("s3")
lam = boto3.client("lambda")

ACCOUNT_ENV_MAP = json.loads(os.environ["ACCOUNT_ENV_MAP"])  # {"111111111111": "prod", ...}

def lambda_handler(event, context):
    detail = event["detail"]
    service = detail["eventSource"].split(".")[0]
    name = detail["eventName"]
    acct = detail["userIdentity"]["accountId"]
    env = ACCOUNT_ENV_MAP.get(acct, "unknown")
    owner = derive_owner(detail["userIdentity"])

    if service == "ec2" and name == "RunInstances":
        for item in detail.get("responseElements", {}).get("instancesSet", {}).get("items", []):
            instance_id = item["instanceId"]
            ec2.create_tags(Resources=[instance_id], Tags=[
                {"Key": "Environment", "Value": env},
                {"Key": "Owner", "Value": owner},
            ])
            # Propagate to child EBS and ENI (Step 4)
            propagate_to_children(instance_id, env, owner)
    elif service == "s3" and name == "CreateBucket":
        bucket = detail["requestParameters"]["bucketName"]
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": [
            {"Key": "Environment", "Value": env},
            {"Key": "Owner", "Value": owner},
        ]})
    elif service == "lambda" and name == "CreateFunction20150331":
        fn = detail["requestParameters"]["functionName"]
        lam.tag_resource(Resource=fn, Tags={"Environment": env, "Owner": owner})
```

Common auto-tagger errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `AccessDenied` on `create-tags` | Lambda execution role missing `ec2:CreateTags` | Add an inline policy granting `ec2:CreateTags` and `ec2:DescribeTags` on `*` |
| Tag stamped but resource still NON_COMPLIANT | Key casing mismatch (Lambda wrote `environment`, Config expects `Environment`) | Normalize the key name in the Lambda before calling `create-tags` |
| EventBridge rule fires but Lambda not invoked | Target not attached or wrong permission | `events:put-targets` plus a `lambda:InvokePermission` for `events.amazonaws.com` |
| Duplicate tags error on replay | `create-tags` is idempotent for the same key/value but errors on different value | Read current tags first; merge; only set deltas |

### Step 4: Propagate tags from EC2 to EBS volumes and ENIs

The `RunInstances` API returns instance IDs, volume IDs, and network
interface IDs. The auto-tagger Lambda must call `ec2:create-tags` on
each child resource. This is the single most common gap in tag
automation — the instance is tagged but the volumes and ENIs are not,
which breaks cost allocation by volume and ABAC on network interfaces.

Propagation logic (extends the Lambda in Step 3):

```python
def propagate_to_children(instance_id, env, owner):
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    tags = [{"Key": "Environment", "Value": env}, {"Key": "Owner", "Value": owner}]
    for r in desc["Reservations"]:
        for i in r["Instances"]:
            volume_ids = [v["Ebs"]["VolumeId"] for v in i.get("BlockDeviceMappings", []) if "Ebs" in v]
            eni_ids = [n["NetworkInterfaceId"] for n in i.get("NetworkInterfaces", [])]
            if volume_ids:
                ec2.create_tags(Resources=volume_ids, Tags=tags)
            if eni_ids:
                ec2.create_tags(Resources=eni_ids, Tags=tags)
```

Propagation coverage matrix:

| Parent resource | Child resources that inherit | API |
|---|---|---|
| EC2 Instance | EBS volumes, ENIs | `ec2:describe-instances` → `ec2:create-tags` |
| RDS DB Instance | Automated snapshots (if tagging enabled) | `rds:add-tags-to-resource` |
| Lambda Function | Versions and aliases (inherit function tags) | No action — automatic |
| S3 Bucket | Objects (only via Bucket Tagging Policy, not direct inheritance) | Configure S3 Bucket Tagging Set, not per-object |

### Step 5: Detect tag drift via Config

Tag drift occurs when a resource's tags are modified after creation —
a human removes `Environment`, or changes `CostCenter` to a non-allowed
value. Config emits a configuration-item change event when recorded tag
state changes.

EventBridge rule on tag drift:

```bash
aws events put-rule --name tag-drift-detector --event-pattern '{
  "source": ["aws.config"],
  "detail-type": ["Config Configuration Item Change"],
  "detail": {
    "configurationItem": {"resourceType": ["AWS::EC2::Instance", "AWS::S3::Bucket"]}
  }
}'
```

A custom Lambda evaluates the new tag set against the schema and emits
a finding to EventBridge or Security Hub. For remediation, hand off to
SSM Automation (Step 6).

### Step 6: Remediate non-compliant and drifted tags via SSM Automation

For each Config rule emitting NON_COMPLIANT on tags, wire a remediation
configuration pointing at an SSM Automation runbook. The managed
`AWS-AttachIAMTags` runbook handles IAM resources; for EC2/S3/RDS, use
a custom runbook or `AWS-ModifyTags` (region availability varies).

Custom runbook sketch (adds the missing tag with a placeholder value):

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Add a missing required tag to an EC2 instance (placeholder value)'
parameters:
  ResourceId:
    type: String
    description: 'EC2 instance ID (injected by Config via RESOURCE_ID)'
  TagKey:
    type: String
    description: 'The missing tag key'
  TagValue:
    type: String
    description: 'Placeholder value; secondary human-correction queue required'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: AddTag
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: CreateTags
      Resources: ['{{ ResourceId }}']
      Tags:
        - Key: '{{ TagKey }}'
          Value: '{{ TagValue }}'
    isCritical: true
    onFailure: abort
```

Wire the remediation configuration:

```bash
aws configservice put-remediation-configurations --remediation-configurations '[{
  "ConfigRuleName": "required-tags-core",
  "TargetType": "SSM_DOCUMENT",
  "TargetId": "Custom-AddRequiredTagEC2",
  "Automatic": false,
  "MaximumAutomaticAttempts": 3,
  "RetryAttemptSeconds": 600,
  "Parameters": {
    "ResourceId": {"ResourceValue": {"Value": "RESOURCE_ID"}},
    "TagKey": {"StaticValue": {"Values": ["Environment"]}},
    "TagValue": {"StaticValue": {"Values": ["unknown"]}},
    "AutomationAssumeRole": {"StaticValue": {"Values": ["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}
  }
}]'
```

**Trigger decision:** default to `Automatic: false` for tag
remediation. Placeholder values (`Environment=unknown`) satisfy Config
but pollute cost reports and ABAC. A secondary human-correction queue
must review and set the correct value. Switch to `Automatic: true` only
for derived-value remediations where the Lambda or runbook can compute
the correct value from the resource context.

### Step 7: Bulk-tag existing backlog via Resource Groups Tagging API

For the existing NON_COMPLIANT backlog, use the Resource Groups Tagging
API. It supports up to 100 resources per `tag-resources` call and
handles cross-service tagging uniformly.

```bash
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123 \
    arn:aws:ec2:us-east-1:111111111111:instance/i-0def456 \
    arn:aws:s3:::app-uploads-bucket-prod \
  --tags Environment=prod,Owner=platform-team
```

Enumerate untagged resources by tag filter (returns resources missing
the specified tag key):

```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=[] \
  --resources-per-page 50
```

Bulk operations in a Lambda (rate-limit aware):

```python
import boto3, time
rgta = boto3.client("resourcegroupstaggingapi")

def bulk_tag(arns, tags, batch_size=20):
    for i in range(0, len(arns), batch_size):
        batch = arns[i:i+batch_size]
        resp = rgta.tag_resources(ResourceARNList=batch, Tags=tags)
        for arn, err in resp.get("FailedResourcesMap", {}).items():
            print(f"FAILED {arn}: {err}")
        time.sleep(0.5)  # avoid throttling
```

### Step 8: Activate cost allocation tags programmatically

Cost allocation tags must be activated on the payer account before they
appear as Cost Explorer dimensions. User-defined tags (custom keys)
require explicit activation; AWS-generated tags (`aws:createdBy`) are
active by default.

```bash
aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[
  {"TagKey": "Environment", "Status": "Active"},
  {"TagKey": "Owner", "Status": "Active"},
  {"TagKey": "CostCenter", "Status": "Active"},
  {"TagKey": "Project", "Status": "Active"}
]'
```

Verify activation:

```bash
aws ce list-cost-allocation-tags --status Active
```

**Gap class — manual Billing-console step:** some payer accounts have
the IAM `ce:UpdateCostAllocationTagsStatus` permission gated behind the
Billing console's "IAM User and Role Access to Billing Information"
setting. If the API returns `AccessDeniedException`, the account
administrator must enable the setting in the Billing console — this
cannot be automated via API. The verdict MUST be `REVIEW_REQUIRED` with
this specific gap.

### Step 9: Enforce cross-account tag consistency via CloudFormation StackSets

For multi-account organizations, deploy the same Config rules and SSM
remediation documents to all accounts via CloudFormation StackSets.
This avoids per-account `put-config-rule` calls and ensures consistency.

```bash
aws cloudformation create-stack-set \
  --stack-set-name tag-compliance-baseline \
  --template-body file://tag-compliance-stackset.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_IAM

aws cloudformation create-stack-instances \
  --stack-set-name tag-compliance-baseline \
  --deployment-targets OrganizationalUnitIds=["ou-xxxx-xxxxxxxx"] \
  --regions us-east-1 us-west-2
```

The StackSet template deploys the Config rules and an SSM document
across all target accounts. For the Organizations TagPolicy, attach it
at the root via `organizations attach-policy` — it cascades natively;
no StackSet is needed for the policy itself.

## Output format

```text
COMPLIANCE: <reference>
SCOPE: <accounts / OUs / regions>
SCHEMA:
  - Required keys: <list>
  - Allowed values: <per-key summary>
  - Case sensitivity: <true | false>
POLICY:
  - Type: Organizations TagPolicy (name) + Config rules (names)
  - Attached to: <root / OU / accounts>
  - enforced_for: <resource types>
DETECTION:
  - Config rules: <list>
  - Drift detection: <enabled | disabled> via <mechanism>
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on <events>
  - Tag propagation: <parent -> child mappings>
  - Remediation: SSM <document name>, trigger <automatic | manual>
PROPAGATION:
  - EC2 -> EBS: <covered>
  - EC2 -> ENI: <covered>
COST:
  - Cost allocation tags: <active | inactive> for <keys>
  - Activation method: <API | manual-console>
CROSS_ACCOUNT:
  - StackSet: <name>, deployment targets <OUs>, regions <list>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippets or YAML for the full stack>
```

### Worked example — AUTOMATION_DEPLOYED, full stack

```text
COMPLIANCE: org-tag-compliance-rollout
SCOPE: org root r-xxxx, all member accounts, us-east-1
SCHEMA:
  - Required keys: Environment, Owner, CostCenter, Project, Application
  - Allowed values: Environment=[dev,staging,prod], CostCenter=[cc-100,cc-200,cc-300]
  - Case sensitivity: true
POLICY:
  - Type: Organizations TagPolicy (baseline-compliance-tag-policy) + Config required-tags-core + allowed-tag-values-environment
  - Attached to: root r-xxxx
  - enforced_for: AWS::EC2::Instance, AWS::S3::Bucket, AWS::RDS::DBInstance, AWS::Lambda::Function
DETECTION:
  - Config rules: required-tags-core, allowed-tag-values-environment
  - Drift detection: enabled via EventBridge on Config CI change for EC2 and S3
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances, CreateBucket, CreateFunction20150331
  - Tag propagation: EC2 -> EBS volumes, EC2 -> ENIs (covered)
  - Remediation: SSM Custom-AddRequiredTagEC2, manual trigger (placeholder values require human correction)
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: covered
COST:
  - Cost allocation tags: active for Environment, Owner, CostCenter, Project
  - Activation method: ce update-cost-allocation-tags-status (API)
CROSS_ACCOUNT:
  - StackSet: tag-compliance-baseline, OUs ou-xxxx-xxxxxxxx, regions us-east-1 us-west-2
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  # 1. Enable and attach TagPolicy
  aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICY
  aws organizations create-policy --type TAG_POLICY --name baseline-compliance-tag-policy --content file://tag-policy.json
  aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx
  # 2. Deploy Config rules
  aws configservice put-config-rule --config-rule <see Step 2>
  # 3. Deploy auto-tagger
  aws events put-rule --name auto-tag-on-create --event-pattern <see Step 3>
  aws lambda create-function --function-name auto-tagger --runtime python3.12 --handler auto_tag.lambda_handler --role arn:aws:iam::111111111111:role/AutoTaggerRole --zip-file fileb://auto_tag.zip
  # 4. Deploy remediation
  aws ssm create-document --name Custom-AddRequiredTagEC2 --document-type Automation --document-format YAML --content file://add-tag-ec2.yaml
  aws configservice put-remediation-configurations --remediation-configurations <see Step 6>
  # 5. Activate cost allocation tags
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status <see Step 8>
```

### Worked example — REVIEW_REQUIRED, manual Billing step

```text
COMPLIANCE: org-tag-compliance-partial
SCOPE: org root r-xxxx, all member accounts, us-east-1
SCHEMA:
  - Required keys: Environment, Owner, CostCenter, Project
  - Allowed values: Environment=[dev,staging,prod]
  - Case sensitivity: true
POLICY:
  - Type: Organizations TagPolicy (baseline-compliance-tag-policy)
  - Attached to: root r-xxxx
  - enforced_for: AWS::EC2::Instance, AWS::S3::Bucket
DETECTION:
  - Config rules: required-tags-core
  - Drift detection: disabled (recorder scope missing S3)
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances
  - Tag propagation: EC2 -> EBS only (ENI propagation missing)
  - Remediation: SSM Custom-AddRequiredTagEC2, manual trigger
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: NOT covered
COST:
  - Cost allocation tags: inactive
  - Activation method: BLOCKED — API returns AccessDeniedException (Billing console IAM access not enabled)
CROSS_ACCOUNT:
  - StackSet: not deployed
VERDICT: REVIEW_REQUIRED
GAP: Three blockers: (1) ENI tag propagation missing in auto-tagger Lambda; (2) cost allocation tag activation blocked — payer account administrator must enable "IAM User and Role Access to Billing Information" in the Billing console before the API can activate tags; (3) Config recorder scope excludes S3, so drift detection on S3 buckets is blind.
TEMPLATE: (partial — see Steps 3, 5, 8 for the missing pieces)
```

## Anti-Patterns — NEVER do these things

- NEVER deploy a TagPolicy without `enforced_for` for any key you intend
  to enforce. Without `enforced_for`, the policy is advisory — operators
  can stamp any value and AWS does not block the operation. The
  "compliance" is documentation theater.

- NEVER assume the `required-tags` managed Config rule validates more
  than 5 keys. It silently ignores keys beyond the 5th. To enforce 6+
  required keys, deploy a second rule or a custom Lambda rule.

- NEVER wire an auto-tagger Lambda without idempotency. EventBridge
  replays events on failure recovery; a non-idempotent Lambda errors on
  duplicate tags or, worse, overwrites a corrected value with a stale
  derived value. Always read current tags first and merge deltas.

- NEVER propagate tags from EC2 to EBS and ENIs without verifying the
  Lambda execution role has `ec2:CreateTags` on the child resource ARNs.
  A role scoped to instances only produces `AccessDenied` on volumes and
  network interfaces silently.

- NEVER activate cost allocation tags and expect immediate Cost Explorer
  updates. The `ce update-cost-allocation-tags-status` API has up to a
  24-hour propagation delay. Re-activating within the window does not
  speed it up and may reset the timer.

- NEVER rely on Config `required-tags` for tag value validation. The
  managed rule checks key presence only. To validate that
  `Environment=prod` (not `Environment=production`), deploy
  `allowed-tag-values` per key or a custom Lambda rule.

- NEVER attach a TagPolicy to a child OU expecting it to merge with the
  root policy. Child-OU policies override root policies for accounts
  under that OU. The effective policy is the closest ancestor's
  declaration. To add a key at the OU level without losing root keys,
  re-declare every parent key in the child policy.

- NEVER deploy a StackSet for Config rules without verifying the
  StackSet execution role exists in every target account. The deploy
  fails per-target with `AccessDenied`, and StackSets reports partial
  failure without a clear per-account error in the top-level output.

- NEVER set `Automatic: true` on a tag-remediation SSM runbook that
  stamps placeholder values. The placeholders satisfy Config but pollute
  Cost Explorer and ABAC. Use manual trigger plus a human-correction
  queue, or a derived-value runbook that computes the correct tag from
  resource context.

- NEVER assume `case_sensitive: false` in a TagPolicy makes Config
  `required-tags` case-insensitive. They are independent systems. Config
  matches the exact key name in `InputParameters`. If the TagPolicy is
  case-insensitive but Config checks `Environment`, a resource tagged
  `environment` is policy-compliant but Config-NON_COMPLIANT.

- NEVER forget to extend the Config recorder scope before wiring drift
  detection for a new resource type. Configuration-item change events
  fire only for recorded types. Tag drift on an unrecorded type is
  invisible.

- NEVER bulk-tag via `tag-resources` without a per-batch failure check.
  The API returns `FailedResourcesMap` per batch; a partial failure is
  silent if the caller does not inspect the response. Always log and
  retry failed ARNs.

- NEVER derive Owner from a service-linked role or EC2 instance profile
  ARN in the auto-tagger. These ARNs identify the launch role, not the
  human owner. Map role ARNs to teams via a lookup table, or require
  the caller to pass an `Owner` tag in the launch request.

- NEVER assume a single `allowed-tag-values` rule validates multiple tag
  keys. The managed rule accepts one `tagKey` per invocation. For N keys
  with allowed-value lists, deploy N rules.

- NEVER ship an auto-tagger without a DLQ on the EventBridge target.
  EventBridge drops events on Lambda failure after the retry policy is
  exhausted. A missing DLQ produces silent tag gaps — the resource is
  created untagged and no one knows.

## Configuration dependency graph

The tag-compliance automation stack has strict ordering dependencies.
Deploy out of order and components fail silently or noisily.

```
[Organizations: enable TAG_POLICY]
        |
        v
[Organizations: create + attach TagPolicy to root]
        |
        +-----------------------------+
        |                             |
        v                             v
[Config: recorder scope covers target types]   [IAM: auto-tagger Lambda role with ec2/s3/lambda tag perms]
        |                             |
        v                             v
[Config: put required-tags + allowed-tag-values rules]   [EventBridge: put-rule on creation events]
        |                             |
        v                             v
[Config: put-remediation-configurations (manual trigger)]   [Lambda: create-function auto-tagger (with EC2->EBS/ENI propagation)]
        |                             |
        v                             v
[SSM: create-document Custom-AddRequiredTag]   [EventBridge: put-targets (Lambda + DLQ)]
        |                             |
        +-----------------------------+
        |
        v
[Cost Explorer: update-cost-allocation-tags-status (payer)]
        |
        v
[CloudFormation: create-stack-set tag-compliance-baseline (OU-wide)]
```

**Hard ordering constraints:**

1. The Organizations TagPolicy type MUST be enabled on the root before
   `create-policy --type TAG_POLICY` succeeds.
2. The Config recorder scope MUST include the target resource types
   before Config rules are deployed, or the rules never evaluate.
3. The auto-tagger Lambda execution role MUST exist and have
   `ec2:CreateTags`, `s3:PutBucketTagging`, and `lambda:TagResource`
   before the EventBridge target is attached, or the first event fails
   with `AccessDenied`.
4. The SSM document MUST exist before `put-remediation-configurations`
   references it, or the remediation config is created but the first
   execution fails with `SSM document not found`.
5. Cost allocation tag activation is independent of the enforcement
   stack but MUST run on the payer account. It can run in parallel with
   the StackSet deployment.

**Parallelizable:** (a) TagPolicy creation and Config rule creation
are independent; (b) the auto-tagger Lambda and the SSM remediation
document can be deployed in parallel once their IAM roles exist.

## Pre-flight safety checks (run before applying any compliance CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-policy`, `attach-policy`, `put-config-rule`,
  `put-remediation-configurations`, `update-cost-allocation-tags-status`),
  emit:
  `CONFIRM: About to <action> for tag compliance in account/OU <target>.
  This affects <consequence>. Proceed? (yes/no)`

- **Back up the current TagPolicy** before modifying:
  `aws organizations describe-policy --policy-id p-xxxxxxx > /tmp/tag-policy-backup-$(date +%s).json`

- **Before flipping a TagPolicy from advisory to enforced** (adding
  `enforced_for`), dry-run by listing NON_COMPLIANT resources via Config
  first. Enforcement blocks non-compliant tag operations, which can
  break CI/CD pipelines that create resources without tags.

- **Before deploying a remediation configuration with `Automatic: true`**,
  test the SSM runbook manually against at least 3 sample NON_COMPLIANT
  resources and verify the tag is applied correctly.

- **For StackSet deployment**, verify the admin and execution roles
  exist in every target account before invoking `create-stack-instances`.

## Appendix A — TagPolicy JSON reference

The full structure of a TagPolicy `content` field:

| Field | Purpose | Required |
|---|---|---|
| `tags.<Key>.TagKey` | The tag key name (must match `<Key>`) | Yes |
| `tags.<Key>.ExpectedStringValues` | Allowed values list | No (presence-only if omitted) |
| `tags.<Key>.EnforcedFor` | Resource types that MUST comply | Yes for enforcement |
| `tags.<Key>.CaseSensitive` | Whether key/value matching is case-sensitive (default: true) | No |

For the full resource-type list and `enforced_for` syntax, see
**references/organizations-tag-policies.md**. For the auto-tagger Lambda
patterns and the EC2-to-EBS/ENI propagation handler, see
**references/auto-tagging-and-propagation.md**.

## Appendix B — Decision tree (which enforcement layer)

```
Is the tag key required on all resources of a type?
├─ Yes → Does the value need an allowlist?
│       ├─ Yes → Deploy TagPolicy with ExpectedStringValues + EnforcedFor
│       │         AND Config allowed-tag-values rule for drift detection
│       └─ No  → Deploy TagPolicy with EnforcedFor only (presence enforcement)
│                 AND Config required-tags rule
└─ No  → Is the tag optional but cost-reportable?
        ├─ Yes → Auto-tagger stamps on creation; cost allocation activation
        └─ No  → No enforcement needed; advisory only
```

## Recent AWS features (2024-2026)

- **TagPolicy `enforced_for` resource-type expansion (2024-2025):**
  AWS added support for additional resource types in `enforced_for`,
  including Lambda layers, Step Functions state machines, and EventBridge
  schemas. Re-check the supported-types list quarterly.
- **Config `allowed-tag-values` enhanced input (2024):** The managed rule
  now accepts regex-style value lists in some regions. Verify region
  availability before relying on regex.
- **Resource Groups Tagging API pagination (2025):** `get-resources` now
  supports a `PaginationToken` with a longer TTL, reducing the need to
  restart bulk enumeration from page 1 on transient failures.
- **Cost Explorer API activation propagation (2025):** The 24-hour
  propagation delay for `update-cost-allocation-tags-status` is now
  visible in the API response as a `ProcessingStatus` field. Poll this
  instead of guessing.
- **CloudFormation StackSets drift detection (2024-2025):** StackSets
  now report per-account drift on the deployed Config rules. Use
  `detect-stack-set-drift` after deployment to catch member-account
  modifications.

## Expert heuristic: tag-policy case sensitivity + EventBridge auto-tagger + Config detection

The most common tag-compliance failure is NOT a missing policy — it is a
policy that looks correct but silently does not enforce, because of
case sensitivity mismatches and missing propagation to child resources.

**The rule (non-negotiable):**

> ALWAYS declare `case_sensitive` explicitly in the TagPolicy (do not
> rely on the default), ALWAYS normalize tag-key casing in the
> EventBridge auto-tagger Lambda before calling `create-tags`, and
> ALWAYS propagate tags from EC2 instances to their child EBS volumes
> and ENIs in the same Lambda handler. A policy that declares
> `Environment` but an auto-tagger that stamps `environment` produces
> a fleet that is TagPolicy-compliant but Config-NON_COMPLIANT — and
> the operator sees conflicting reports with no obvious cause.

**Why this rule exists:** AWS Organizations Tag Policies, Config
`required-tags`, Config `allowed-tag-values`, and Cost Explorer are
four independent systems that each interpret tag keys independently.
The TagPolicy may be case-insensitive (`case_sensitive: false`) while
Config `required-tags` always checks the exact key name in
`InputParameters`. A resource tagged `environment=prod` is
TagPolicy-compliant but Config-NON_COMPLIANT if the Config rule checks
for `Environment`. The auto-tagger is the bridge — it must normalize
casing to match ALL downstream systems.

**Concrete case-sensitivity matrix:**

| System | Default case sensitivity | Override mechanism |
|---|---|---|
| Organizations TagPolicy | `case_sensitive: true` | Set `case_sensitive: false` per key |
| Config `required-tags` | Exact match on `InputParameters` key name | No override — must match exactly |
| Config `allowed-tag-values` | Exact match on key and value | No override |
| Cost Explorer (user-defined tags) | Case-insensitive on key, case-sensitive on value | No override |
| Resource Groups Tagging API | Case-sensitive on key | No override |

**EC2-to-child propagation diagnostic:**

If Cost Explorer shows instance costs tagged but EBS volume costs
untagged, the auto-tagger is not propagating to child resources. Verify
the Lambda handler:

1. Reads `BlockDeviceMappings[].Ebs.VolumeId` from
   `ec2:describe-instances` for each new instance.
2. Reads `NetworkInterfaces[].NetworkInterfaceId` from the same call.
3. Calls `ec2:create-tags` with all volume IDs and all ENI IDs in
   batch (the API accepts up to 100 resources per call).
4. Has `ec2:CreateTags` permission on `arn:aws:ec2:*:*:volume/*` and
   `arn:aws:ec2:*:*:network-interface/*`, not just `instance/*`.

**Detection of enforcement-scope breach post-deploy:** CloudWatch alarm
on `Config.ComplianceNonCompliantResources` for `required-tags-core`
increasing by > N% in one evaluation cycle (suggests a new resource
type in scope but the auto-tagger is not firing on its creation event).
Also alarm on EventBridge `Invocations` vs `FailedInvocations` for the
auto-tagger rule — a spike in failures means the Lambda role lost a
permission or the EventBridge target was detached.

**Surface in the output:** for any recommended tag-compliance
automation, include `CASE_SENSITIVITY: <true | false>` (the TagPolicy
setting), `CASE_NORMALIZATION: <yes | no>` (whether the auto-tagger
normalizes key casing), `PROPAGATION_COVERAGE: <parent -> child list>`,
and `VALIDATION_STATUS: <advisory | enforced>`. If
`VALIDATION_STATUS` is `advisory` or `PROPAGATION_COVERAGE` is
incomplete, do NOT mark the recommendation as AUTOMATION_DEPLOYED.

## Domain

AWS CloudOps / Governance Automation — Tag compliance enforcement and
remediation.

## AWS documentation

- **AWS Organizations Tag Policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html
- **AWS Config required-tags rule** — https://docs.aws.amazon.com/config/latest/developerguide/required-tags.html
- **AWS Config allowed-tag-values rule** — https://docs.aws.amazon.com/config/latest/developerguide/allowed-tag-values.html
- **Resource Groups Tagging API** — https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/overview.html
- **Cost Explorer Cost Allocation Tags** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-allocated-tags.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
