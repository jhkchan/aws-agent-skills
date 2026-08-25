---
name: tag-compliance-automator
description: 'Automates AWS tag compliance end-to-end: Organizations tag policies with case-sensitive key/value validation and enforced_for scoping, Resource Groups Tagging API bulk operations, Config managed rules (required-tags, allowed-tag-values) plus custom Lambda rules for 6+ keys, EventBridge + Lambda auto-tagging on EC2/S3/Lambda creation with inherited-tag propagation (EC2 to EBS and ENIs), tag drift detection via Config CI change events, remediation via SSM Automation, cost allocation tag activation via Cost Explorer API, and cross-account consistency via CloudFormation StackSets. Emits AUTOMATION_DEPLOYED with deployment templates or REVIEW_REQUIRED with the specific gap. Use when building tag compliance automation, enforcing a tag schema, wiring auto-tagging, or remediating tag drift across an organization.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline policy design. Live deployment uses aws organizations enable-policy-type, create-policy, update-policy, attach-policy, aws resourcegroupstaggingapi tag-resources, untag-resources, get-resources, aws configservice put-config-rule, put-remediation-configurations, aws ce update-cost-allocation-tags-status, aws ssm create-document, start-automation-execution, aws lambda...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Designing Organizations tag policies with case-sensitive key/value validation, building EventBridge + Lambda auto-tagging pipelines with inherited-tag propagation (EC2 to EBS/ENI), running Resource Groups Tagging API bulk operations, wiring Config required-tags and allowed-tag-values rules with drift detection, remediating tag drift via SSM Automation, activating cost allocation tags programmatically, or enforcing cross-account tag consistency via CloudFormation StackSets.
  activation_triggers: tag compliance automation, Organizations tag policy case_sensitive, auto-tag on creation EventBridge Lambda, tag propagation EC2 EBS ENI, Resource Groups Tagging API bulk, tag-resources untag-resources get-resources, required-tags allowed-tag-values Config rule, tag drift detection remediation, cost allocation tag activation, cross-account tag consistency StackSets, tag schema enforcement, Environment Owner CostCenter Project tags
  invocation_schema: 'Input: either (a) a tag compliance requirement ("enforce Environment, Owner, CostCenter, Project tags on all EC2, S3, and RDS resources with auto-tagging and drift remediation", "propagate tags from EC2 to EBS volumes and ENIs on creation", "activate cost allocation tags programmatically"), OR (b) an existing tag policy, Config rule, or EventBridge auto-tagger to audit and harden. Output: deterministic COMPLIANCE block per requirement — POLICY/DETECTION/AUTOMATION/ PROPAGATION/REMEDIATION/COST/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (templates ready and validated) or REVIEW_REQUIRED (specific gap cited, e.g., manual Billing-console step or untested custom runbook).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Organizations, Tag Policy, TagPolicy, case_sensitive, enforced_for, allowed_values, Resource Groups Tagging API, tag-resources, untag-resources, get-resources, AWS Config, required-tags, allowed-tag-values, tag drift, EventBridge, Lambda auto-tagging, tag propagation, EC2 EBS ENI, cost allocation tags, Cost Explorer API, CloudFormation StackSets, SSM Automation, tag compliance, tag schema, Environment Owner CostCenter Project
  tags: aws-organizations, tag-policy, resource-groups-tagging-api, aws-config, eventbridge, lambda, cost-explorer, cloudformation-stacksets, ssm-automation, automate
---

# Tag Compliance Automator

## Mindset

**One-line takeaway:** tag compliance is a four-layer pipeline —
**define** (Organizations TagPolicy with `enforced_for` and case-sensitive
key/value rules) → **detect** (Config `required-tags` and
`allowed-tag-values` rules flag non-compliant resources; Config CI changes
catch tag drift) → **propagate** (EventBridge + Lambda auto-tags new
resources and propagates inherited tags from EC2 to EBS volumes and ENIs)
→ **remediate** (SSM Automation adds or corrects missing tags; Config
re-evaluates and flips COMPLIANT). A gap in ANY layer produces a silent
failure: the policy is published but advisory, auto-tagging stamps tags
that humans later overwrite, drift goes undetected, or cost allocation
reports stay empty because no one activated the tag keys in Billing.

- **Organizations TagPolicy** without `enforced_for` is advisory only.
  AWS does not block non-compliant tag operations. The policy is
  documentation, not enforcement.
- **Case sensitivity** is a silent gap. A TagPolicy with
  `case_sensitive: true` treats `Environment` and `environment` as
  different keys. Config `required-tags` checks the exact key name in
  InputParameters. Auto-taggers must normalize casing before stamping.
- **EC2 tags do NOT propagate to EBS volumes or ENIs.** The `RunInstances`
  API tags only the instance. An EventBridge Lambda must call
  `ec2:create-tags` on child resources.
- **Cost allocation tags are NOT active by default.** A perfectly tagged
  fleet produces zero cost-dimension data until an administrator activates
  the tag keys via the Billing API or console.

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

## Critical rules at a glance (do NOT bury these)

1. **`enforced_for` is the only enforcement hook in a TagPolicy.** A
   policy with `allowed_values` but no `enforced_for` entries is
   advisory. Always list resource types under `enforced_for` for every
   tag key you want enforced.
2. **`case_sensitive` defaults to `true` and mismatches break
   silently.** If the policy declares `Environment` and a resource is
   tagged `environment`, the policy does not match. Config
   `required-tags` also checks the exact key name. Normalize casing in
   the auto-tagger before stamping.
3. **Config `required-tags` checks at most 5 tag keys per rule.** To
   enforce 6+ keys, deploy a second rule (`required-tags-ext`) or a
   custom Lambda rule.
4. **EC2 tags do NOT propagate to EBS volumes or ENIs.** The
   `RunInstances` API tags only the instance. An EventBridge-driven
   Lambda must call `ec2:create-tags` on child resources.
5. **Cost allocation tag activation is account-scoped and per-key.** The
   `ce update-cost-allocation-tags-status` API activates a tag key for
   the payer account only. Propagation delay is up to 24 hours.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Existing tag policies | `organizations list-policies --filter TAG_POLICY` | Avoid overwriting an in-use policy |
| Organization root ID | `organizations list-roots` | Attachment target for the policy |
| Tag policy type enabled | `organizations describe-organization` `AvailablePolicyTypes` | Must enable TAG_POLICY before attaching |
| Config recorder status | `configservice describe-configuration-recorders` | Rules cannot evaluate without a recorder |
| Current cost allocation tag status | `ce list-cost-allocation-tags` | Avoid redundant activation calls |
| Sample resource tag coverage | `resourcegroupstaggingapi get-resources` | Baseline before enforcement |
| SSM service role ARN | `iam get-role` on the SSM automation role | Remediation execution identity |

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

- **A TagPolicy attached to the org root cascades to all OUs and
  accounts, but a policy attached to a specific OU OVERRIDES (not
  merges) the root policy.** The effective tag policy is the policy
  attached to the closest ancestor. To add a key at the OU level
  without losing root keys, re-declare every parent key in the child.

- **`enforced_for` accepts resource types in `AWS::service::resource`
  format.** A typo like `AWS::EC2::instance` (lowercase) is silently
  ignored. Cross-reference the canonical resource-type list.

- **Config `required-tags` uses `InputParameters` as a JSON-encoded
  string.** Passing a map where the API expects
  `"{\"tag1Key\":\"Environment\"}"` silently drops the input.

- **The Resource Groups Tagging API is eventually consistent.** Tagging
  returns `SUCCESS` immediately but a follow-up `get-resources` within
  seconds may not reflect new tags. Sleep 10-15 seconds before re-querying.

- **EventBridge auto-taggers that derive Owner from the IAM principal
  must handle assumed-role sessions.** The `userIdentity.sessionContext`
  has `sessionIssuer.arn` (the role). Deriving a human owner from a role
  ARN requires a mapping table.

- **`allowed-tag-values` is a Config managed rule that accepts ONE tag
  key per invocation.** For 4 tag keys' value validation, deploy 4
  separate rules.

- **The `ce update-cost-allocation-tags-status` API has a propagation
  delay of up to 24 hours.** Do not re-activate or assume failure within
  that window. Poll the `ProcessingStatus` field.

- **Config configuration-item change events fire only for recorded
  resource types.** Tag drift on an unrecorded type is invisible.
  Extend the recorder scope before wiring drift detection.

### Step 1: Design the Organizations TagPolicy

The TagPolicy JSON declares per tag key: `TagKey`, `ExpectedStringValues`
(optional allowed values), and `EnforcedFor` (resource types that must
comply). Wrap under a `tags` object.

```json
{
  "tags": {
    "Environment": {
      "TagKey": "Environment",
      "ExpectedStringValues": ["dev", "staging", "prod"],
      "EnforcedFor": ["AWS::EC2::Instance", "AWS::S3::Bucket", "AWS::RDS::DBInstance", "AWS::Lambda::Function"]
    },
    "Owner": {
      "TagKey": "Owner",
      "EnforcedFor": ["AWS::EC2::Instance", "AWS::S3::Bucket"]
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
aws organizations create-policy --type TAG_POLICY --name baseline-compliance-tag-policy \
  --description "Enforced tag keys: Environment, Owner, CostCenter, Project" --content file://tag-policy.json
aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx
```

| TagPolicy shape | Behavior | Verdict impact |
|---|---|---|
| `allowed_values` set, `enforced_for` empty | Advisory — no operation blocked | REVIEW_REQUIRED (enforcement gap) |
| `allowed_values` set, `enforced_for` populated | Enforced — non-compliant op returns `ConstraintViolation` | AUTOMATION_DEPLOYED |
| No `allowed_values`, `enforced_for` populated | Key presence enforced, value not validated | AUTOMATION_DEPLOYED (presence only) |

### Step 2: Choose the Config rule pattern

| Pattern | Rule type | Use case | Limit |
|---|---|---|---|
| Required keys presence | `required-tags` (managed) | Enforce N tag keys exist | Max 5 keys per rule |
| Allowed values per key | `allowed-tag-values` (managed) | Enforce value allowlist | One key per rule |
| Custom multi-key validation | Custom Lambda rule | 6+ required keys, regex, conditional logic | Lambda maintenance |
| Tag drift detection | Custom Lambda on Config CI change | Detect tag removal or value change | Requires recorder coverage |

Deploy `required-tags` for the first 5 keys:

```bash
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "required-tags-core",
  "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
  "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance", "AWS::S3::Bucket", "AWS::RDS::DBInstance", "AWS::Lambda::Function"]},
  "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"
}'
```

For the 6th+ required key, deploy a second rule (`required-tags-ext`)
or a custom Lambda rule.

### Step 3: Wire the EventBridge auto-tagger

The auto-tagger fires on resource-creation events and stamps inherited
or derived tags. It must be idempotent and case-normalized.

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

Lambda handler must: (a) derive Environment from an account-to-env map,
(b) derive Owner from the IAM identity (normalize role sessions via
lookup), (c) normalize key casing before calling `create-tags`, and
(d) propagate to child resources (Step 4). Common errors:

| Error | Cause | Fix |
|---|---|---|
| `AccessDenied` on `create-tags` | Lambda role missing `ec2:CreateTags` | Add inline policy for `ec2:CreateTags` on `*` |
| Tag stamped but resource still NON_COMPLIANT | Key casing mismatch | Normalize key name in Lambda before `create-tags` |
| EventBridge rule fires but Lambda not invoked | Target not attached or wrong permission | `events:put-targets` plus `lambda:InvokePermission` |

### Step 4: Propagate tags from EC2 to EBS volumes and ENIs

The `RunInstances` API returns instance IDs, volume IDs, and ENI IDs.
The auto-tagger Lambda must call `ec2:create-tags` on each child
resource. This is the most common propagation gap — the instance is
tagged but volumes and ENIs are not.

```python
def propagate_to_children(instance_id, tags):
    desc = ec2.describe_instances(InstanceIds=[instance_id])
    for r in desc["Reservations"]:
        for i in r["Instances"]:
            volume_ids = [v["Ebs"]["VolumeId"] for v in i.get("BlockDeviceMappings", []) if "Ebs" in v]
            eni_ids = [n["NetworkInterfaceId"] for n in i.get("NetworkInterfaces", [])]
            if volume_ids:
                ec2.create_tags(Resources=volume_ids, Tags=tags)
            if eni_ids:
                ec2.create_tags(Resources=eni_ids, Tags=tags)
```

| Parent | Child inherits | API |
|---|---|---|
| EC2 Instance | EBS volumes, ENIs | `ec2:create-tags` on `VolumeId` and `NetworkInterfaceId` |
| RDS DB Instance | Automated snapshots | `rds:add-tags-to-resource` |
| Lambda Function | Versions, aliases | Automatic — no action needed |

### Step 5: Detect tag drift via Config

Tag drift occurs when tags are modified after creation. Config emits a
configuration-item change event when recorded tag state changes.

```bash
aws events put-rule --name tag-drift-detector --event-pattern '{
  "source": ["aws.config"],
  "detail-type": ["Config Configuration Item Change"],
  "detail": {"configurationItem": {"resourceType": ["AWS::EC2::Instance", "AWS::S3::Bucket"]}}
}'
```

A custom Lambda evaluates the new tag set against the schema and emits
a finding to EventBridge or Security Hub. For remediation, hand off to
SSM Automation (Step 6).

### Step 6: Remediate non-compliant and drifted tags via SSM Automation

For each Config rule emitting NON_COMPLIANT on tags, wire a remediation
configuration pointing at an SSM Automation runbook. The custom runbook
adds the missing tag with a placeholder value:

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Add a missing required tag (placeholder value)'
parameters:
  ResourceId: {type: String, description: 'Injected by Config via RESOURCE_ID'}
  TagKey: {type: String}
  TagValue: {type: String, description: 'Placeholder; secondary human-correction queue required'}
  AutomationAssumeRole: {type: String}
mainSteps:
  - name: AddTag
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: CreateTags
      Resources: ['{{ ResourceId }}']
      Tags: [{Key: '{{ TagKey }}', Value: '{{ TagValue }}'}]
    isCritical: true
    onFailure: abort
```

Wire the remediation:

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

**Trigger decision:** default to `Automatic: false` for tag remediation.
Placeholder values (`Environment=unknown`) satisfy Config but pollute
cost reports and ABAC. Switch to `Automatic: true` only for
derived-value remediations where the runbook can compute the correct
value from resource context.

### Step 7: Bulk-tag existing backlog via Resource Groups Tagging API

```bash
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    arn:aws:ec2:us-east-1:111111111111:instance/i-0abc123 \
    arn:aws:s3:::app-uploads-bucket-prod \
  --tags Environment=prod,Owner=platform-team

aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=[] \
  --resources-per-page 50
```

The API supports up to 100 resources per call. Always check
`FailedResourcesMap` in the response — partial failures are silent if
the caller does not inspect.

### Step 8: Activate cost allocation tags programmatically

```bash
aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[
  {"TagKey": "Environment", "Status": "Active"},
  {"TagKey": "Owner", "Status": "Active"},
  {"TagKey": "CostCenter", "Status": "Active"},
  {"TagKey": "Project", "Status": "Active"}
]'
```

**Gap class — manual Billing-console step:** some payer accounts gate
`ce:UpdateCostAllocationTagsStatus` behind the Billing console's "IAM
User and Role Access to Billing Information" setting. If the API
returns `AccessDeniedException`, an administrator must enable it in the
Billing console. The verdict MUST be `REVIEW_REQUIRED`.

### Step 9: Enforce cross-account tag consistency via CloudFormation StackSets

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

The Organizations TagPolicy itself cascades natively; the StackSet is
for Config rules and SSM documents across accounts.

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
  - Remediation: SSM Custom-AddRequiredTagEC2, manual trigger
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: covered
COST:
  - Cost allocation tags: active for Environment, Owner, CostCenter, Project
  - Activation method: ce update-cost-allocation-tags-status (API)
CROSS_ACCOUNT:
  - StackSet: tag-compliance-baseline, OUs ou-xxxx-xxxxxxxx, regions us-east-1 us-west-2
VERDICT: AUTOMATION_DEPLOYED
GAP: None — placeholder remediation values require a secondary human-correction queue.
TEMPLATE:
  aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICY
  aws organizations create-policy --type TAG_POLICY --name baseline-compliance-tag-policy --content file://tag-policy.json
  aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx
  aws configservice put-config-rule --config-rule <see Step 2>
  aws events put-rule --name auto-tag-on-create --event-pattern <see Step 3>
  aws lambda create-function --function-name auto-tagger --runtime python3.12 --handler auto_tag.lambda_handler --role arn:aws:iam::111111111111:role/AutoTaggerRole --zip-file fileb://auto_tag.zip
  aws ssm create-document --name Custom-AddRequiredTagEC2 --document-type Automation --document-format YAML --content file://add-tag-ec2.yaml
  aws configservice put-remediation-configurations --remediation-configurations <see Step 6>
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status <see Step 8>
```

### Worked example — REVIEW_REQUIRED, manual Billing step

```text
COMPLIANCE: org-tag-compliance-partial
SCOPE: org root r-xxxx, all member accounts, us-east-1
POLICY:
  - Type: Organizations TagPolicy (baseline-compliance-tag-policy)
  - enforced_for: AWS::EC2::Instance, AWS::S3::Bucket
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances
  - Tag propagation: EC2 -> EBS only (ENI propagation missing)
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: NOT covered
COST:
  - Cost allocation tags: inactive
  - Activation method: BLOCKED — API returns AccessDeniedException (Billing console IAM access not enabled)
VERDICT: REVIEW_REQUIRED
GAP: Three blockers: (1) ENI tag propagation missing in auto-tagger Lambda; (2) cost allocation tag activation blocked — payer account administrator must enable "IAM User and Role Access to Billing Information" in the Billing console; (3) Config recorder scope excludes S3, so drift detection on S3 is blind.
TEMPLATE: (partial — see Steps 3, 5, 8 for the missing pieces)
```

## Anti-Patterns — NEVER do these things

- NEVER deploy a TagPolicy without `enforced_for` for any key you intend
  to enforce. Without it, the policy is advisory and AWS does not block
  non-compliant operations.

- NEVER assume `required-tags` validates more than 5 keys. It silently
  ignores keys beyond the 5th. Deploy a second rule or a custom Lambda.

- NEVER wire an auto-tagger Lambda without idempotency. EventBridge
  replays events on failure recovery; a non-idempotent Lambda errors on
  duplicate tags or overwrites corrected values with stale derived ones.

- NEVER propagate tags from EC2 to EBS and ENIs without verifying the
  Lambda execution role has `ec2:CreateTags` on child resource ARNs. A
  role scoped to instances only produces silent `AccessDenied`.

- NEVER activate cost allocation tags and expect immediate Cost Explorer
  updates. The API has a 24-hour propagation delay.

- NEVER rely on Config `required-tags` for tag value validation. The
  managed rule checks key presence only. Use `allowed-tag-values` or a
  custom Lambda rule for value enforcement.

- NEVER attach a TagPolicy to a child OU expecting merge with the root
  policy. Child-OU policies OVERRIDE root policies. To add a key without
  losing root keys, re-declare every parent key.

- NEVER set `Automatic: true` on a tag-remediation runbook that stamps
  placeholder values. Placeholders satisfy Config but pollute Cost
  Explorer and ABAC. Use manual trigger plus a human-correction queue.

- NEVER assume `case_sensitive: false` in a TagPolicy makes Config
  `required-tags` case-insensitive. They are independent systems. Config
  always matches the exact key name in `InputParameters`.

- NEVER ship an auto-tagger without a DLQ on the EventBridge target.
  EventBridge drops events on Lambda failure after retry exhaustion,
  producing silent tag gaps.

## Configuration dependency graph

```
[Organizations: enable TAG_POLICY]
        |
        v
[Organizations: create + attach TagPolicy to root]
        |
        +-----------------------------+
        |                             |
        v                             v
[Config: recorder scope covers target types]   [IAM: auto-tagger Lambda role]
        |                             |
        v                             v
[Config: put required-tags + allowed-tag-values rules]   [EventBridge: put-rule + Lambda + DLQ]
        |                             |
        v                             v
[Config: put-remediation-configurations (manual)]   [SSM: create-document Custom-AddRequiredTag]
        |
        v
[Cost Explorer: update-cost-allocation-tags-status (payer)]
        |
        v
[CloudFormation: create-stack-set (OU-wide)]
```

**Hard ordering constraints:**

1. TAG_POLICY type MUST be enabled before `create-policy`.
2. Config recorder scope MUST include target types before rules deploy.
3. Auto-tagger Lambda role MUST exist before EventBridge target attaches.
4. SSM document MUST exist before `put-remediation-configurations`.
5. Cost allocation activation runs independently on the payer account.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for tag compliance in <target>.
  This affects <consequence>. Proceed? (yes/no)`
- **Back up the current TagPolicy** before modifying:
  `aws organizations describe-policy --policy-id p-xxxxxxx > /tmp/tag-policy-backup.json`
- **Before flipping from advisory to enforced**, dry-run by listing
  NON_COMPLIANT resources via Config first.
- **For StackSet deployment**, verify admin and execution roles exist in
  every target account.

## Appendix A — TagPolicy JSON reference

| Field | Purpose | Required |
|---|---|---|
| `tags.<Key>.TagKey` | The tag key name (must match `<Key>`) | Yes |
| `tags.<Key>.ExpectedStringValues` | Allowed values list | No |
| `tags.<Key>.EnforcedFor` | Resource types that MUST comply | Yes for enforcement |
| `tags.<Key>.CaseSensitive` | Key/value case sensitivity (default: true) | No |

For the full resource-type list and auto-tagger Lambda patterns, see
**references/organizations-tag-policies.md** and
**references/auto-tagging-and-propagation.md**.

## Appendix B — Decision tree (which enforcement layer)

```
Is the tag key required on all resources of a type?
├─ Yes → Does the value need an allowlist?
│       ├─ Yes → TagPolicy with ExpectedStringValues + EnforcedFor
│       │         AND Config allowed-tag-values for drift detection
│       └─ No  → TagPolicy with EnforcedFor (presence) + Config required-tags
└─ No  → Auto-tagger stamps on creation; cost allocation activation
```

## Recent AWS features (2024-2026)

- **TagPolicy `enforced_for` resource-type expansion:** Additional
  types including Lambda layers, Step Functions state machines. Re-check
  the supported-types list quarterly.
- **Cost Explorer API `ProcessingStatus`:** The 24-hour propagation
  delay is now visible in the API response. Poll instead of guessing.
- **CloudFormation StackSets drift detection:** Per-account drift on
  deployed Config rules via `detect-stack-set-drift`.
- **Resource Groups Tagging API pagination:** Longer TTL on
  `PaginationToken`, reducing bulk-enumeration restarts.

## Expert heuristic: tag-policy case sensitivity + EventBridge auto-tagger + Config detection

The most common tag-compliance failure is NOT a missing policy — it is a
policy that looks correct but silently does not enforce, because of
case-sensitivity mismatches and missing propagation to child resources.

**The rule (non-negotiable):**

> ALWAYS declare `case_sensitive` explicitly in the TagPolicy, ALWAYS
> normalize tag-key casing in the EventBridge auto-tagger Lambda before
> calling `create-tags`, and ALWAYS propagate tags from EC2 instances to
> their child EBS volumes and ENIs in the same Lambda handler. A policy
> that declares `Environment` but an auto-tagger that stamps
> `environment` produces a fleet that is TagPolicy-compliant but
> Config-NON_COMPLIANT.

**Case-sensitivity matrix:**

| System | Default case sensitivity | Override |
|---|---|---|
| Organizations TagPolicy | `case_sensitive: true` | `CaseSensitive: false` per key |
| Config `required-tags` | Exact match on InputParameters key | No override |
| Config `allowed-tag-values` | Exact match on key and value | No override |
| Cost Explorer (user-defined) | Case-insensitive on key, case-sensitive on value | No override |
| Resource Groups Tagging API | Case-sensitive on key | No override |

**EC2-to-child propagation diagnostic:** if Cost Explorer shows instance
costs tagged but EBS volume costs untagged, the auto-tagger is not
propagating. Verify the Lambda reads `BlockDeviceMappings[].Ebs.VolumeId`
and `NetworkInterfaces[].NetworkInterfaceId`, calls `ec2:create-tags`
in batch, and has `ec2:CreateTags` on `volume/*` and
`network-interface/*`.

**Surface in the output:** include `CASE_SENSITIVITY`, `CASE_NORMALIZATION`,
`PROPAGATION_COVERAGE`, and `VALIDATION_STATUS`. If
`VALIDATION_STATUS` is advisory or `PROPAGATION_COVERAGE` is incomplete,
do NOT mark the recommendation as AUTOMATION_DEPLOYED.

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
