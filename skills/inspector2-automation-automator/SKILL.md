---
name: inspector2-automation-automator
description: >-
  Designs and deploys Amazon Inspector v2 automation workflows —
  enabling Inspector across EC2, ECR, and Lambda resources;
  EventBridge routing for finding events; severity-based auto-
  remediation (Critical = patch via SSM Automation, High = notify
  with Slack/email); ECR image scan on push integration; Lambda
  code scan finding handling; finding suppression for accepted
  risks; Inspector to Security Hub finding forwarding; multi-account
  via Organizations delegated admin; patch baseline association
  for OS-level remediation; SSM Automation runbook design for
  OS patching; container image rebuild trigger via CodeBuild;
  finding lifecycle (open/suppressed/closed) and SLA enforcement.
  Emits AUTOMATION_DEPLOYED with a workflow template (CLI or
  CloudFormation) or REVIEW_REQUIRED with the specific gap. Use
  when building Inspector-driven remediation, wiring SSM patch
  baselines to Inspector findings, configuring ECR rescan, or
  forwarding Inspector findings to Security Hub.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline workflow design.
  Live deployment uses aws inspector2 enable, disable, list-findings,
  batch-get-finding-details, update-configuration, list-coverage,
  aws ssm create-document, start-automation-execution,
  create-patch-baseline, update-patch-baseline, register-patch-baseline-for-patches,
  aws events put-rule, put-targets, aws securityhub
  batch-import-findings, aws ecr put-image-scanning-configuration,
  start-image-scan, and aws codebuild start-build — AWS CLI v2,
  SSO or key-based credentials.
keywords:
  - Amazon Inspector
  - Inspector v2
  - Inspector2
  - vulnerability scanning
  - ECR image scan
  - Lambda code scan
  - EventBridge finding
  - SSM patch baseline
  - SSM Automation runbook
  - Security Hub
  - delegated admin
  - finding suppression
  - finding lifecycle
  - severity-based remediation
  - container rebuild
  - patch remediation
tags: [amazon-inspector, security-automation, ssm-patch, security-hub, eventbridge, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Designing Inspector v2 automation, wiring SSM Automation
    runbooks to Inspector findings, building severity-based
    remediation (Critical=patch, High=notify), configuring ECR
    image scan on push, handling Lambda code scan findings,
    forwarding Inspector findings to Security Hub, building
    multi-account Inspector via Organizations delegated admin,
    configuring patch baseline associations, or suppressing
    accepted-risk findings.
  activation_triggers:
    - "automate Inspector finding"
    - "Inspector v2 remediation"
    - "ECR image scan on push"
    - "Lambda code scan finding"
    - "Inspector to Security Hub"
    - "severity-based remediation"
    - "SSM patch baseline for Inspector"
    - "Inspector delegated admin"
    - "Inspector finding suppression"
    - "container image rebuild"
    - "Inspector EventBridge"
    - "Critical finding auto-patch"
  invocation_schema: >-
    Input: either (a) an Inspector finding or finding type (e.g.,
    CVE-2026-1234 on i-0abc123, or "all Critical findings in
    prod-OU"), OR (b) an automation requirement ("auto-patch
    Critical Inspector findings, notify on High"). Output:
    deterministic REMEDIATION block per finding class —
    FINDING/SEVERITY/DETECTION/RESPONSE/SSM_RUNBOOK/VERIFICATION/
    VERDICT — where VERDICT is AUTOMATION_DEPLOYED (workflow
    template ready) or REVIEW_REQUIRED (specific gap cited).
---

# Inspector2 Automation Automator

## Mindset

**One-line takeaway:** every Inspector automation is a five-stage
pipeline — **enable** (Inspector coverage across EC2/ECR/Lambda) →
**detect** (finding emitted, EventBridge routes it) → **triage**
(severity + resource context determines response) → **remediate**
(SSM Automation patch, container rebuild, or notify) → **verify**
(finding transitions to CLOSED, Security Hub reflects the fix). A gap
in ANY stage produces silent exposure: the CVE is found, but the
Lambda function never gets rebuilt, or the patch runs but the
finding stays OPEN because the instance was never rescanned.

- **Detection** without **EventBridge routing** is a dashboard, not
  automation. The Inspector console shows findings; nobody looks
  unless paged.
- **Severity-based response** is the operational backbone:
  Critical findings get SSM-driven patching within hours; High gets
  Slack notification within a day; Medium/Low get queued for the
  next patch window. Treating all severities the same burns out the
  on-call.
- **Verification is the closing gate.** Inspector findings have a
  lifecycle (OPEN → SUPPRESSED or CLOSED). A patch that succeeds
  at the OS level but leaves the finding OPEN means the rescan
  never ran, or the finding is suppressed-but-not-resolved.

## Quick navigation

| You want to... | Go to |
|---|---|
| Enable Inspector across EC2 / ECR / Lambda | Step 2 |
| Pick severity-based response | Step 4 (severity matrix) |
| Wire EventBridge rule for findings | Step 5 |
| Build SSM patch baseline for OS findings | Step 6 |
| SSM Automation runbook for patching | Step 7 |
| ECR image scan on push + rebuild trigger | Step 8 |
| Lambda code scan finding handling | Step 9 |
| Inspector to Security Hub forwarding | Step 10 |
| Finding suppression for accepted risks | Step 11 |
| Multi-account via delegated admin | Step 12 |
| Finding lifecycle and SLA enforcement | Step 13 |
| Patch baseline association to instance | Step 14 |
| Avoid common automation pitfalls | Anti-Patterns |
| Recent features (rescan, code scan) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Inspector ECR scans are PUSH-TIME, not continuous.** A scanned
   image stays "scanned" until a NEW image is pushed. New CVEs
   discovered tomorrow are NOT detected for images pushed today
   until a manual rescan runs. Wire a scheduled rescan via
   `start-image-scan` for production-critical repositories.
2. **Lambda code scans are STATIC analysis at deploy time, NOT
   runtime.** They detect vulnerable dependency versions in the
   deployment package. They do NOT detect runtime behavior, RCE
   exploitation, or supply-chain attacks against the function's
   runtime. Pair with CloudTrail and GuardDuty for runtime coverage.
3. **SSM patch baseline + maintenance window is the canonical
   remediation path for EC2 OS findings.** SSM Automation runbook
   `AWS-RunPatchBaseline` with `Operation: Install` applies
   patches; the runbook does NOT reboot by default (set
   `RebootOption: RebootIfNeeded`).
4. **Inspector findings have a 7-day SUPPRESSION window by default
   before re-alerting.** Suppressing a finding marks it
   `SUPPRESSED` but does NOT close it. The finding re-opens after
   the suppression expires unless explicitly closed.
5. **Security Hub finding ingestion from Inspector has ~5 minute
   propagation latency.** A "patched" Inspector finding may remain
   `OPEN` in Security Hub for several minutes. Verify with
   `securityhub get-findings` filtered by `AwsAccountId` and
   `GeneratorId` before declaring the workflow complete.

## Pre-flight: data requirements

Designing an Inspector automation requires these inputs:

| Input | Source | Why |
|---|---|---|
| Inspector coverage | `inspector2 list-coverage` | Confirm EC2/ECR/Lambda enabled |
| Delegated admin status | `inspector2 list-delegated-admin-accounts` | Multi-account routing |
| Finding type / sample finding ARN | `inspector2 list-findings` | Concrete workflow design |
| Resource type targeted | `finding.Resources[0].Type` | Drives remediation strategy |
| Severity distribution | `inspector2 list-findings --filter-criteria severity=...` | Triage priority |
| ECR repos + scan frequency | `ecr describe-image-scan-findings`, `put-image-scanning-configuration` | Continuous scan gap analysis |
| SSM agent health on EC2 | `ssm describe-instance-information` | Patch baseline can't run on unmanaged instances |
| Existing patch baselines | `ssm describe-patch-baselines` | Avoid duplicates |
| Security Hub integration | `inspector2 batch-get-configuration` → `SecurityHubStatus` | Forwarding status |

**If the input is malformed** (missing finding type, ambiguous
target resource), emit:

```text
FINDING: <reference>
VERDICT: ERROR
REASON: Cannot design Inspector automation — finding type and target resource are required inputs.
GAP: Re-supply the Inspector finding ARN or finding type plus target resource identifier (instance ID, ECR repo+tag, Lambda function ARN).
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Inspector behaviors

These behaviors change the workflow design if ignored:

- **Inspector ECR scans run automatically on push when scanning is
  enabled.** A repo with `scanOnPush: true` scans each new image
  within minutes. A repo with `scanOnPush: false` requires manual
  `start-image-scan`. The default for new repos depends on account
  settings — verify per repo.

- **Inspector rescan for ECR is NOT automatic when new CVEs are
  published.** An image scanned at push-time is "scanned for life"
  unless explicitly rescanned. New CVE databases do NOT trigger
  re-evaluation. For production repos, schedule weekly rescans via
  EventBridge → Lambda → `start-image-scan`.

- **Inspector Lambda code scans run on function UPDATE, not
  continuously.** A function deployed with a vulnerable package
  stays "vulnerable" in Inspector until the function is updated
  with a patched version. New CVEs against the deployed version
  are detected on the next rescan cycle (Inspector rescans Lambda
  functions every few days automatically).

- **Inspector does NOT detect vulnerabilities in Lambda layers
  directly.** The layer's package is attributed to the function.
  A shared vulnerable layer triggers findings on every function
  that consumes it — useful for blast-radius analysis.

- **Inspector finding severity is NOT configurable.** Severity
  comes from the CVE database (CVSS score). A "Critical" CVE stays
  Critical regardless of business context. Use the
  `ResourceTag` filter or finding suppression to override triage
  for accepted-risk resources.

- **SSM patch baseline with `Operation: Scan` does NOT modify the
  instance.** It populates the SSM patch compliance dashboard. Use
  `Operation: Install` to apply patches. Wire Scan first
  (low-risk), then Install (state-changing).

- **Inspector → Security Hub integration is one-way.** Inspector
  forwards findings to Security Hub automatically when integration
  is enabled. Closing a finding in Inspector closes it in Security
  Hub (within ~5 minutes). Closing in Security Hub does NOT close
  in Inspector.

- **Inspector delegated admin requires an Organizational unit
  scope.** The delegated admin account manages Inspector for all
  member accounts in the Organization. Member accounts cannot
  disable Inspector or modify configurations.

- **Inspector findings have `Title`, `Description`, and `Remediation`
  fields.** The `Remediation.Recommendation.Text` field contains
  vendor-specific guidance (e.g., "Update package `openssl` to
  version 1.1.1n"). Parse this to drive the SSM Automation
  parameters dynamically.

- **`AWS-RunPatchBaseline` patches only packages in the approved
  patch baseline.** A CVE affecting a package NOT in the baseline
  (e.g., a third-party repo) is not patched by SSM. The CVE will
  re-appear in Inspector after rescan. Extend the patch baseline
  with the required source repository.

- **Inspector cannot scan an EC2 instance without SSM agent
  running.** Inspector relies on SSM for both scanning and patching.
  An instance without SSM agent appears in `list-coverage` as
  `NOT_DETECTED` — no findings will ever surface.

- **Container image rebuild requires CI/CD pipeline access.**
  Inspector detects the vulnerable image; CodeBuild (or equivalent)
  rebuilds it from a patched base image. The pipeline trigger is
  typically EventBridge → CodeBuild `start-build`.

### Step 1: Classify the finding source

For each Inspector finding, classify the source:

| Source class | Resource type | Example finding | Notes |
|---|---|---|---|
| EC2 OS package | `AwsEc2Instance` | CVE-2026-1234 on `openssl` | Best fit for SSM patch baseline |
| ECR container image | `AwsEcrContainerImage` | CVE in base image `amazonlinux:2` | Rebuild trigger, not patch |
| Lambda function code | `AwsLambdaFunction` | Vulnerable dependency in package | Function update required |
| Network reachability | `AwsEc2Instance` | Open SSH to internet | Security group fix (not patch) |
| Secret detection | `AwsLambdaFunction` / `AwsEcrContainerImage` | Hardcoded credential | Code fix required |

If the source is ECR, the remediation is "rebuild the image" not
"patch in place." Mark this in the workflow design.

### Step 2: Enable Inspector (EC2 / ECR / Lambda)

```bash
aws inspector2 enable \
  --account-ids 111111111111 \
  --client-token $(uuidgen) \
  --ec2 \
  --ecr \
  --lambda
```

Verify coverage:

```bash
aws inspector2 list-coverage \
  --filter-criteria accountId=111111111111
```

For multi-account via delegated admin:

```bash
# In the management account
aws inspector2 enable \
  --account-ids 111111111111 222222222222 333333333333 \
  --ec2 --ecr --lambda

# Designate delegated admin
aws organizations register-delegated-administrator \
  --account-id 111111111111 \
  --service-principal inspector2.amazonaws.com
```

**Common pitfall:** the delegated admin account must be a member of
the Organization, and Inspector must be enabled in the management
account first. A standalone delegated admin call fails silently.

### Step 3: Map the resource type to a remediation strategy

| Resource type | Finding class | Strategy |
|---|---|---|
| `AwsEc2Instance` | OS package CVE | SSM `AWS-RunPatchBaseline` (Step 6-7) |
| `AwsEc2Instance` | Network reachability | Custom SSM doc to revoke SG rule (manual trigger) |
| `AwsEcrContainerImage` | Container CVE | Trigger CodeBuild rebuild from patched base (Step 8) |
| `AwsLambdaFunction` | Dependency CVE | Update function code with patched package (Step 9) |
| `AwsLambdaFunction` | Secret in code | Code review + secret removal (manual trigger) |

**If no automated remediation exists** for the finding class (e.g.,
network reachability finding on a production security group), the
verdict tilts toward REVIEW_REQUIRED until the custom SSM document
or manual procedure is built.

### Step 4: Decide severity-based response (the severity matrix)

| Severity | SLA | Response | Automation |
|---|---|---|---|
| `Critical` | 24 hours | Auto-patch via SSM within 4 hours of detection | EventBridge → SSM `AWS-RunPatchBaseline` |
| `High` | 7 days | Notify via Slack/email within 1 day; queue for next patch window | EventBridge → Lambda → Slack |
| `Medium` | 30 days | Roll into monthly maintenance window | Cron → SSM |
| `Low` | 90 days | Triage at quarterly review | Report only |

**Decision rule:** default to **automatic patching for Critical**
only after the SSM patch baseline has been validated in non-prod.
High/Medium/Low should always require human review before patching
in production.

### Step 5: Wire EventBridge rule for findings

```bash
aws events put-rule \
  --name inspector-critical-auto-patch \
  --event-pattern '{
    "source": ["aws.inspector2"],
    "detail-type": ["Inspector Finding"],
    "detail": {
      "severity": ["CRITICAL"],
      "status": ["OPEN"]
    }
  }'

aws events put-targets \
  --rule inspector-critical-auto-patch \
  --targets '[{"Id":"inspector-patch-ssm","Arn":"arn:aws:ssm:us-east-1:111111111111:automation-definition/AWS-RunPatchBaseline","RoleArn":"arn:aws:iam::111111111111:role/service-role/AmazonInspectorEventBridgeInvokeSSM"}]'
```

Or route to Lambda for triage logic:

```bash
aws events put-targets \
  --rule inspector-critical-auto-patch \
  --targets '[{"Id":"inspector-triage-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:inspector-finding-triage","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:inspector-finding-dlq"}}]'
```

Lambda handler:

```python
import boto3, json
ssm = boto3.client('ssm')
inspector = boto3.client('inspector2')

def lambda_handler(event, context):
    finding = event['detail']
    finding_arn = finding['findingArn']
    severity = finding['severity']
    resource = finding['resources'][0]

    if resource['type'] == 'AWS_EC2_INSTANCE':
        instance_id = resource['details']['awsEc2Instance']['instanceId']

        if severity == 'CRITICAL':
            # Auto-patch
            ssm.start_automation_execution(
                DocumentName='AWS-RunPatchBaseline',
                DocumentVersion='1',
                Parameters={
                    'InstanceId': [instance_id],
                    'Operation': ['Install'],
                    'RebootOption': ['RebootIfNeeded']
                },
                Mode='Auto'
            )
            return {'statusCode': 200, 'body': f'Started patch for {instance_id}'}

    elif resource['type'] == 'AWS_ECR_CONTAINER_IMAGE':
        # Trigger rebuild via CodeBuild
        cb = boto3.client('codebuild')
        cb.start_build(
            projectName='container-rebuild-pipeline',
            environmentVariablesOverride=[{
                'name': 'VULNERABLE_IMAGE',
                'value': resource['details']['awsEcrContainerImage']['imageName']
            }]
        )

    return {'statusCode': 200, 'body': 'No action'}
```

### Step 6: SSM patch baseline for OS findings

```bash
# Create a patch baseline aligned to Amazon Linux 2
aws ssm create-patch-baseline \
  --name "al2-critical-patches" \
  --operating-system AMAZON_LINUX_2 \
  --patch-groups "critical-patch-group" \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "PatchFilters": [{
          "Key": "CLASSIFICATION",
          "Values": ["Security"]
        }, {
          "Key": "SEVERITY",
          "Values": ["Critical", "Important"]
        }]
      },
      "ApproveAfterDays": 0,
      "ComplianceLevel": "CRITICAL"
    }]
  }'
```

Register the baseline as the default for the OS:

```bash
aws ssm register-patch-baseline-for-patches \
  --baseline-id "pb-abc123def456" \
  --operating-systems AMAZON_LINUX_2
```

**Patch baseline gotchas:**
- `ApproveAfterDays: 0` auto-approves immediately. Use 7 days for
  High, 30 for Medium to allow soak time.
- `ComplianceLevel: CRITICAL` flags non-compliant instances as
  "Critical" in the SSM compliance dashboard.
- Patch groups are tags (`Patch Group: critical-patch-group`).
  Instances must be tagged to receive patches from this baseline.

### Step 7: SSM Automation runbook for patching

```bash
aws ssm start-automation-execution \
  --document-name AWS-RunPatchBaseline \
  --document-version "1" \
  --parameters '{
    "InstanceId": ["i-0abc123def456"],
    "Operation": ["Install"],
    "RebootOption": ["RebootIfNeeded"],
    "SnapshotId": [""]
  }' \
  --mode Auto
```

For fleet-wide patching with approval:

```yaml
# Custom SSM Automation runbook
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Patch EC2 instances flagged by Inspector Critical findings'
parameters:
  InstanceIds:
    type: StringList
    description: 'List of instance IDs to patch'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: CreateSnapshot
    action: aws:createImage
    inputs:
      InstanceId: '{{ InstanceIds[0] }}'
      ImageName: 'pre-patch-snapshot-{{ global:DATE_TIME }}'
      NoReboot: true
    outputs:
      - Name: ImageId
        Selector: '$.ImageId'
        Type: String
  - name: PatchInstances
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunPatchBaseline
      InstanceIds: '{{ InstanceIds }}'
      Parameters:
        Operation: Install
        RebootOption: RebootIfNeeded
    isCritical: true
    onFailure: abort
  - name: VerifyPatch
    action: aws:waitForAwsResourceProperty
    inputs:
      Service: ssm
      Api: DescribeInstancePatches
      InstanceId: '{{ InstanceIds[0] }}'
      PropertySelector: '$.Patches[?(@.State=="Installed")].State'
      DesiredValues: ['Installed']
      Waiter: 'InstancePatchesState'
```

### Step 8: ECR image scan on push + rebuild trigger

Enable scan-on-push per repository:

```bash
aws ecr put-image-scanning-configuration \
  --repository-name prod-app \
  --image-scanning-configuration scanOnPush=true
```

For scheduled rescan of existing images:

```bash
# EventBridge cron rule: weekly rescan
aws events put-rule \
  --name ecr-weekly-rescan \
  --schedule-expression "cron(0 6 ? * MON *)" \
  --state ENABLED

aws events put-targets \
  --rule ecr-weekly-rescan \
  --targets '[{"Id":"ecr-rescan-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:ecr-batch-rescan"}]'
```

Lambda handler:

```python
import boto3
ecr = boto3.client('ecr')

def lambda_handler(event, context):
    repos = ecr.describe_repositories(maxResults=50)
    for repo in repos['repositories']:
        images = ecr.list_images(repositoryName=repo['repositoryName'], maxResults=100)
        for img in images['imageIds']:
            try:
                ecr.start_image_scan(
                    repositoryName=repo['repositoryName'],
                    imageId={'imageDigest': img['imageDigest']}
                )
            except Exception as e:
                print(f'Skip {img}: {e}')
    return {'statusCode': 200}
```

Container rebuild trigger via CodeBuild:

```bash
aws events put-rule \
  --name inspector-ecr-rebuild-trigger \
  --event-pattern '{
    "source": ["aws.inspector2"],
    "detail-type": ["Inspector Finding"],
    "detail": {
      "severity": ["CRITICAL"],
      "status": ["OPEN"],
      "resources": {
        "type": ["AWS_ECR_CONTAINER_IMAGE"]
      }
    }
  }'

aws events put-targets \
  --rule inspector-ecr-rebuild-trigger \
  --targets '[{"Id":"codebuild-rebuild","Arn":"arn:aws:codebuild:us-east-1:111111111111:project/container-rebuild-pipeline","RoleArn":"arn:aws:iam::111111111111:role/service-role/CodeBuildEventBridgeInvoke"}]'
```

### Step 9: Lambda code scan finding handling

Lambda findings require function code update — there is no in-place
patch. The workflow:

```python
# Lambda triggered by EventBridge on Lambda code scan finding
import boto3, os
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')

def lambda_handler(event, context):
    finding = event['detail']
    function_arn = finding['resources'][0]['details']['awsLambdaFunction']['functionArn']
    function_name = function_arn.split(':')[-1] if ':' in function_arn else function_arn

    # Notify — Lambda patches require code redeploy
    sns.publish(
        TopicArn=os.environ['NOTIFY_TOPIC'],
        Message=f'Inspector finding on Lambda {function_name}: {finding["title"]}\n\n'
                f'Remediation: {finding.get("remediation", {}).get("recommendation", {}).get("text", "n/a")}\n'
                f'Redeploy required: update dependency in build pipeline.'
    )

    # Optional: create a ticket via Jira/ServiceNow API
    return {'statusCode': 200}
```

**Lambda finding gotchas:**
- Code scan findings are NOT auto-remediable via SSM.
- The fix requires the function's CI/CD pipeline to update the
  dependency version.
- Suppression is the only "non-fix" option (Step 11).

### Step 10: Inspector to Security Hub forwarding

Enable integration:

```bash
aws inspector2 batch-update-configuration \
  --ec2-configuration '[]' \
  --ecr-configuration '[]' \
  --lambda-configuration '[]'

# Security Hub integration is enabled by default when both are active
aws securityhub describe-hub  # verify Security Hub is enabled
```

Verify findings are forwarding:

```bash
aws securityhub get-findings \
  --filters 'GeneratorId=[{"Value":"aws-inspector","Comparison":"PREFIX"}]' \
  --query 'Findings[0].[Id,Severity,GeneratorId]' --output json
```

**Integration rules:**
- Closing an Inspector finding closes the Security Hub finding
  (within 5 minutes).
- Suppressing an Inspector finding sets the Security Hub finding
  workflow status to `SUPPRESSED`.
- Inspector-generated Security Hub findings have
  `ProductArn: arn:aws:securityhub:<region>::product/aws/inspector`.

### Step 11: Finding suppression for accepted risks

For findings on resources where remediation is not feasible (e.g.,
legacy system with no patch available):

```bash
aws inspector2 update-finding \
  --finding-arn arn:aws:inspector2:us-east-1:111111111111:finding/abc123 \
  --status SUPPRESSED

# Or batch update
aws inspector2 batch-update-findings \
  --finding-arns arn:aws:inspector2:us-east-1:111111111111:finding/abc123 arn:aws:inspector2:us-east-1:111111111111:finding/def456 \
  --suppression-reason "Legacy system decommission scheduled 2027-Q1"
```

**Suppression rules:**
- Suppressed findings stay in Inspector with `status: SUPPRESSED`.
- They are excluded from default finding queries.
- They re-open if the finding changes (e.g., new evidence).
- Document suppression rationale in `suppressionReason` for audit.

For automated suppression (accepted-risk list):

```python
import boto3
inspector = boto3.client('inspector2')

ACCEPTED_RISKS = {
    'arn:aws:inspector2:us-east-1:111111111111:finding/abc123': 'Legacy CVE, decommission scheduled',
    # ... loaded from DynamoDB
}

def lambda_handler(event, context):
    for arn, reason in ACCEPTED_RISKS.items():
        inspector.update_finding(
            findingArn=arn,
            status='SUPPRESSED',
            suppressionReason=reason
        )
    return {'statusCode': 200}
```

### Step 12: Multi-account via delegated admin

```bash
# In the management account — designate delegated admin
aws organizations register-delegated-administrator \
  --account-id 111111111111 \
  --service-principal inspector2.amazonaws.com

# In the delegated admin account — enable for all member accounts
aws inspector2 enable \
  --account-ids $(aws organizations list-accounts --query 'Accounts[].Id' --output text | tr '\t' ' ') \
  --ec2 --ecr --lambda
```

Verify member account coverage:

```bash
aws inspector2 list-coverage \
  --filter-criteria accountId=222222222222
```

**Multi-account gotchas:**
- Member accounts cannot disable Inspector once the delegated admin
  has enabled it.
- The delegated admin account is the only place to view aggregated
  findings.
- Security Hub aggregated findings follow the Security Hub
  delegated admin (which may be a different account from the
  Inspector delegated admin).

### Step 13: Finding lifecycle and SLA enforcement

Inspector finding lifecycle:

```
OPEN → (auto-resolved or patched) → CLOSED
OPEN → (suppressed for accepted risk) → SUPPRESSED → (re-opens if finding changes) → OPEN
```

SLA enforcement via scheduled Lambda:

```python
import boto3, os
from datetime import datetime, timedelta
inspector = boto3.client('inspector2')
sns = boto3.client('sns')

SLA = {
    'CRITICAL': 1,   # days
    'HIGH': 7,
    'MEDIUM': 30,
    'LOW': 90,
}

def lambda_handler(event, context):
    now = datetime.utcnow()
    for severity, sla_days in SLA.items():
        cutoff = (now - timedelta(days=sla_days)).isoformat()
        resp = inspector.list_findings(
            filterCriteria={
                'severity': [{'comparison': 'EQUALS', 'value': severity}],
                'status': [{'comparison': 'EQUALS', 'value': 'OPEN'}],
                'updatedAt': [{'comparison': 'LESS_THAN', 'value': cutoff}]
            }
        )
        for finding in resp['findings']:
            sns.publish(
                TopicArn=os.environ['SLA_TOPIC'],
                Message=f'SLA breached: {severity} finding {finding["findingArn"]} open for > {sla_days} days'
            )
    return {'statusCode': 200}
```

### Step 14: Patch baseline association to instances

```bash
# Tag instances for patch group
aws ec2 create-tags \
  --resources i-0abc123def456 i-0def456ghi789 \
  --tags Key=Patch Group,Value=critical-patch-group

# Verify patch baseline association
aws ssm describe-effective-patch-instances \
  --instance-id i-0abc123def456
```

**Patch group gotchas:**
- An instance can be in only one patch group per OS.
- The patch group maps to a baseline via `register-patch-baseline-for-patches`.
- Removing the tag detaches the instance from the baseline.

## Output format

```text
FINDING: <reference>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW>
DETECTION:
  - Source: <aws.inspector2 via EventBridge>
  - Resource: <type + identifier>
  - CVE: <id + package>
RESPONSE:
  - Action: <SSM patch | CodeBuild rebuild | Lambda update | notify>
  - SLA: <days>
  - Automation: EventBridge → SSM | Lambda → CodeBuild
SSM_RUNBOOK: <AWS-RunPatchBaseline | custom document>
VERIFICATION:
  - Rescan: aws inspector2 list-findings --filter-criteria status=OPEN
  - Security Hub: aws securityhub get-findings --filter-criteria RecordState=ACTIVE
MULTI_ACCOUNT: <single | delegated-admin>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the workflow>
```

### Worked example — AUTOMATION_DEPLOYED, Critical EC2 CVE auto-patch

```text
FINDING: ec2-critical-cve-patch
SEVERITY: CRITICAL
DETECTION:
  - Source: aws.inspector2 via EventBridge (rule inspector-critical-auto-patch)
  - Resource: AWS_EC2_INSTANCE i-0abc123def456
  - CVE: CVE-2026-1234 on openssl (CVSS 9.8)
RESPONSE:
  - Action: SSM patch via AWS-RunPatchBaseline
  - SLA: 24 hours (4-hour automation window)
  - Automation: EventBridge → SSM start-automation-execution
SSM_RUNBOOK: AWS-RunPatchBaseline with Operation=Install, RebootOption=RebootIfNeeded
VERIFICATION:
  - Rescan: aws inspector2 list-findings --filter-criteria findingArn=...
  - Security Hub: aws securityhub get-findings --filter-criteria GeneratorId=aws-inspector
MULTI_ACCOUNT: single (111111111111)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name inspector-critical-auto-patch --event-pattern '{"source":["aws.inspector2"],"detail-type":["Inspector Finding"],"detail":{"severity":["CRITICAL"],"status":["OPEN"]}}'
  aws ssm start-automation-execution --document-name AWS-RunPatchBaseline --parameters '{"InstanceId":["i-0abc123def456"],"Operation":["Install"],"RebootOption":["RebootIfNeeded"]}' --mode Auto
```

### Worked example — REVIEW_REQUIRED, missing delegated admin

```text
FINDING: multiaccount-finding-triage
SEVERITY: HIGH
DETECTION:
  - Source: aws.inspector2 in management account
  - Resource: AWS_ECR_CONTAINER_IMAGE across 15 member accounts
  - CVE: CVE-2026-5678 on log4j in shared service image
RESPONSE:
  - Action: notify + rebuild trigger
  - SLA: 7 days
  - Automation: blocked (delegated admin not configured)
SSM_RUNBOOK: n/a (container finding — CodeBuild rebuild)
VERIFICATION: blocked
MULTI_ACCOUNT: REVIEW_REQUIRED — delegated admin not yet configured
VERDICT: REVIEW_REQUIRED
GAP: Inspector delegated admin not configured. Without delegated admin, findings must be queried per-member-account individually. Configure via aws organizations register-delegated-administrator --account-id 111111111111 --service-principal inspector2.amazonaws.com before enabling fleet-wide automation.
TEMPLATE: (blocked until delegated admin configured)
```

## Anti-Patterns — NEVER do these things

- NEVER auto-patch Critical Inspector findings in production
  without first validating the patch baseline in non-prod. A
  misconfigured baseline can apply a bad kernel patch that
  bricks the instance. Always run a 1-week soak in non-prod first.

- NEVER assume ECR image scan results are continuous. A scanned
  image stays "clean" forever in the Inspector dashboard unless
  explicitly rescanned. Wire a weekly scheduled rescan via
  EventBridge → Lambda → `start-image-scan` for production repos.

- NEVER confuse Lambda code scan findings with runtime findings.
  Lambda code scans are static analysis on the deployment package.
  They do NOT detect runtime exploitation. Pair with CloudTrail +
  GuardDuty for runtime coverage.

- NEVER suppress findings without documenting the rationale in
  `suppressionReason`. A finding suppressed silently is invisible
  in default queries; the next operator will not know why.

- NEVER auto-rebuild production container images on every Critical
  finding. A misconfigured EventBridge rule can trigger dozens of
  concurrent CodeBuild runs, exhausting the build fleet. Rate-limit
  via SQS buffer or step function.

- NEVER rely on Inspector SSM coverage alone for EC2. Inspector
  requires SSM agent. Instances without the agent (e.g., Bottlerocket
  without SSM, custom AMIs) are invisible to Inspector. Wire a
  separate Config rule for SSM agent health.

- NEVER forget the SSM patch baseline `ApproveAfterDays` setting.
  A baseline with `ApproveAfterDays: 7` will NOT patch CVEs that
  are less than 7 days old. For Critical CVEs, use a separate
  baseline with `ApproveAfterDays: 0`.

- NEVER close Inspector findings manually. Inspector auto-closes
  findings when the underlying vulnerability is no longer detected
  (post-rescan). Manual close creates drift between Inspector and
  Security Hub.

- NEVER wire Security Hub as the only finding source for
  remediation. Security Hub has ~5-minute propagation latency from
  Inspector. For real-time automation, use the
  `aws.inspector2` EventBridge source directly.

- NEVER use Inspector severity as the sole trigger. A
  business-context overlay (e.g., "Critical on production
  instance" vs "Critical on dev sandbox") is required. Use the
  Lambda triage pattern (Step 5) to add resource tags to the
  decision.

- NEVER assume the Inspector delegated admin can disable Inspector
  in a member account. The delegated admin can ENABLE but member
  accounts can NOT disable once the delegated admin has enabled.
  This is a security feature, not a bug — but it confuses
  operators expecting symmetric control.

- NEVER omit the DLQ on EventBridge → Lambda for Inspector finding
  routing. Inspector findings can fire in bursts (e.g., when a
  popular base image CVE is published). Lambda throttling without
  DLQ produces silent finding loss.

- NEVER assume `AWS-RunPatchBaseline` patches everything. It only
  patches packages in the configured patch baseline. Third-party
  repos, unmanaged packages, and packages outside the baseline are
  NOT patched. Extend the baseline or use a custom SSM document.

- NEVER apply Critical patches without a snapshot. Use
  `aws:createImage` (or `aws:backupEc2Instance`) as the first
  step in any patch automation runbook. A bad patch without a
  rollback snapshot is unrecoverable without a rebuild.

- NEVER use the deprecated Inspector Classic APIs (`inspector`)
  for new automation. Inspector v2 (`inspector2`) is the
  supported API. Inspector Classic is end-of-life.

- NEVER forget the SSM service role for `AWS-RunPatchBaseline`.
  The instance's instance profile needs `AmazonSSMManagedInstanceCore`
  plus the patching permissions. Missing profile → `ACCESS_DENIED`
  on patch execution.

- NEVER wire Inspector to SSM patching without verifying instance
  inventory. An instance with stale SSM agent or unreachable from
  SSM endpoints silently fails patching. The Inspector finding
  stays OPEN indefinitely. Wire a CloudWatch alarm on
  `SSM > InstancePatchCompliance` for stale instances.

## Pre-flight safety checks (run before applying any Inspector CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`inspector2 enable`, `disable`, `update-finding`,
  custom SSM `start-automation-execution`, suppressing findings),
  emit:
  `CONFIRM: About to <action> for finding/coverage <id> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`

- **Snapshot the target EC2 instances** before any patching:
  `aws ec2 create-image --instance-id i-0abc123 --name "pre-inspector-patch-$(date +%s)" --no-reboot`

- **Before auto-patching Critical findings in production**, run
  the patch baseline in `Operation: Scan` mode for 1 week in
  pre-prod to validate the baseline contents. Then promote to
  `Install` mode.

- **Before deploying Inspector multi-account**, verify the
  delegated admin account is correctly designated via
  `aws inspector2 list-delegated-admin-accounts`.

- **For container rebuild automation**, dry-run the CodeBuild
  project manually with a test finding payload to verify the
  build pipeline produces a patched image without exhausting
  concurrent build limits.

## Appendix A — Common Inspector automation patterns (summary)

The most-used automation patterns. The default for any new
automation should be SNS notification; escalate to SSM patching
only after notification alone has failed to remediate.

| Pattern | Severity | Reversible | Notes |
|---|---|---|---|
| SNS notify only | Any | Yes | Slack/email |
| SSM patch (EC2) | Critical | Yes (snapshot rollback) | Use `AWS-RunPatchBaseline` |
| ECR image rebuild | Critical/High | Yes (rollback tag) | Trigger CodeBuild |
| Lambda function update | Critical/High | Yes (version rollback) | CI/CD pipeline required |
| Finding suppression | Any | Yes (re-open) | Document rationale |
| Security Hub forwarding | All | Yes | One-way Inspector → SecHub |
| SSM patch via maintenance window | Medium | Yes | Scheduled, not event-driven |

For the full pattern catalog (input parameters, severity pairing,
safety profiles, and execution role requirements), see
**references/inspector2-automation-patterns.md**. Always
cross-reference the pattern's parameter contract with your
`start-automation-execution` or Lambda handler payload.

## Appendix B — Decision tree (which automation pattern)

```
Is the finding on EC2, ECR, or Lambda?
├─ EC2 OS package → Severity?
│       ├─ Critical → SSM AWS-RunPatchBaseline (Step 7) with snapshot
│       ├─ High     → Notify + queue for next maintenance window
│       └─ Med/Low  → Roll into monthly patch cycle
├─ ECR container image → Severity?
│       ├─ Critical/High → Trigger CodeBuild rebuild from patched base (Step 8)
│       └─ Med/Low       → Notify repo owner; queue for next image rebuild
└─ Lambda function → Code scan or runtime?
        ├─ Code scan → Notify function owner (Step 9); CI/CD redeploy required
        └─ Runtime   → Not Inspector's scope; route to GuardDuty
```

## Recent AWS features (2024-2026)

- **Inspector Lambda code scans GA (2024):** Static analysis on
  Lambda deployment packages covering dependency CVEs. NOT runtime
  analysis. Limited to functions updated after Inspector Lambda
  coverage was enabled.

- **Inspector ECR automated re-scan (2024):** Inspector automatically
  rescans ECR images when the CVE database is updated (within 24
  hours of a new CVE publication). Previously required manual
  `start-image-scan`. Verify with `aws ecr describe-image-scan-findings`
  post-CVE release.

- **Inspector delegated admin enhancements (2024-2025):** Multi-account
  coverage reporting via `list-coverage` aggregated across all member
  accounts. Faster propagation of coverage changes (5-15 minutes).

- **Inspector finding aggregation in Security Hub (2025):** Improved
  finding correlation — Inspector findings now include
  `RelatedFindings` linking network reachability findings to
  CVE-based findings on the same instance.

- **Inspector Lambda runtime monitoring preview (2025-2026):**
  Limited preview of runtime behavior analysis for Lambda
  functions, complementing the static code scan. Check regional
  availability before designing workflows that depend on it.

- **SSM patch baseline integration with Inspector (2025):**
  `AWS-RunPatchBaseline` now reads Inspector finding metadata to
  prioritize patches. The patch document parameter
  `IncludeInspectorFindings: true` filters the patch operation to
  only Inspector-flagged packages.

## Expert heuristic: automation blast radius

Inspector-driven auto-patching is the highest-leverage security
control but also the highest-risk. A misconfigured patch automation
can apply a bad kernel patch across an entire OU within hours,
bricking production instances with no rollback window.

**The rule (non-negotiable):**

> ALWAYS run Inspector-driven auto-patching in `Scan` mode for 1 week
  in non-prod before promoting to `Install` mode. ALWAYS snapshot
  instances before any patch automation. NEVER enable auto-patch on
  production without a validated rollback path (AMI + CloudFormation
  redeploy).

**Why this rule exists:** Inspector findings fire in bursts (when a
popular base image CVE is published, dozens of findings can surface
across an account in minutes). EventBridge → SSM automation can
patch all of them concurrently, exceeding instance capacity for
reboot or applying a bad patch before operators notice.

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| Tag-based patch groups | `Patch Group: critical-prod-canary` tag | Restricts patch to canary instances |
| Non-prod OU promotion | Deploy in non-prod OU first, promote after soak | Zero prod exposure until validated |
| `Operation: Scan` before `Install` | SSM patch baseline mode | Validates baseline contents without state change |
| Rate-limit via SQS | EventBridge → SQS → Lambda → SSM | Caps concurrent patch executions |
| Maintenance window gate | Route Critical findings into the next window | Human gate per cycle |
| Snapshot gate | `aws:createImage` as first runbook step | Recovery path within minutes |

**Pre-production validation protocol (3-cycle rule):**

1. **Cycle 1 — SCAN-ONLY in non-prod:** Deploy Inspector + patch
   baseline in `Operation: Scan` mode. Monitor the SSM patch
   compliance dashboard for 1 week. Verify findings correlate with
   Inspector output.

2. **Cycle 2 — INSTALL in non-prod:** Promote baseline to `Install`.
   Plant a known-vulnerable instance. Verify the patch runs, the
   instance reboots, the Inspector finding transitions to CLOSED
   within 24 hours, and Security Hub reflects the closure.

3. **Cycle 3 — SCAN-ONLY in prod:** Deploy the validated baseline to
   production in `Operation: Scan` mode. Monitor for 1 week.
   Verify no false-positive patch compliance flags. Then promote
   to `Install` with snapshot gate enabled.

**CloudFormation scoping pattern (recommended for fleet rollout):**

```yaml
# Inspector-driven patching with snapshot gate and non-prod soak
Resources:
  PatchBaseline:
    Type: AWS::SSM::PatchBaseline
    Properties:
      Name: inspector-critical-patches
      OperatingSystem: AMAZON_LINUX_2
      ApprovalRules:
        PatchRules:
          - PatchFilterGroup:
              PatchFilters:
                - Key: CLASSIFICATION
                  Values: [Security]
                - Key: SEVERITY
                  Values: [Critical]
            ApproveAfterDays: 0
            ComplianceLevel: CRITICAL
      PatchGroups:
        - critical-patch-group

  PatchAutomationRunbook:
    Type: AWS::SSM::Document
    Properties:
      DocumentType: Automation
      Content:
        schemaVersion: '0.3'
        mainSteps:
          - name: Snapshot
            action: aws:createImage
            inputs:
              InstanceId: '{{ InstanceId }}'
              ImageName: 'pre-inspector-patch-{{ global:DATE_TIME }}'
              NoReboot: true
          - name: Patch
            action: aws:runCommand
            inputs:
              DocumentName: AWS-RunPatchBaseline
              InstanceIds: ['{{ InstanceId }}']
              Parameters:
                Operation: Install
                RebootOption: RebootIfNeeded

  EventBridgeRule:
    Type: AWS::Events::Rule
    Properties:
      Name: inspector-critical-auto-patch
      EventPattern:
        source: [aws.inspector2]
        detail-type: [Inspector Finding]
        detail:
          severity: [CRITICAL]
          status: [OPEN]
          resources:
            type: [AWS_EC2_INSTANCE]
      State: ENABLED  # Flip to ENABLED only after Cycle 2 validation
      Targets:
        - Arn: !Sub 'arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:automation-definition/AWS-RunPatchBaseline'
          RoleArn: !GetAtt EventBridgeInvokeSSMRole.Arn
```

**Detection of blast-radius breach post-deploy:** CloudWatch alarm on
`SSM > CommandInvocationCount > N in 5 minutes` (suggests a bad
EventBridge rule firing on a burst of findings). Also alarm on
`SSM > InstancePatchCompliance > NonCompliantCount > N` in 24 hours
(suggests a bad patch baseline applied account-wide). Both alarms
should page the on-call security team and trigger an EventBridge
rule that disables the Inspector auto-patch rule via
`aws events disable-rule`.

**Surface in the output:** for any recommended automation, include
`BLAST_RADIUS: <scope>` (e.g., `OU-wide`,
`tag-scoped:env=prod`, `single-instance`, `single-account`) and
`VALIDATION_STATUS: <scan-non-prod | install-non-prod | scan-prod |
install-prod>`. If `VALIDATION_STATUS` is not `install-prod`, do
NOT mark the auto-patch recommendation as deployable.

## Domain

AWS CloudOps / Security Automation — Inspector-driven remediation.

## AWS documentation

- **Amazon Inspector** — https://docs.aws.amazon.com/inspector/latest/user/scaling-securing.html
- **Inspector v2 API** — https://docs.aws.amazon.com/inspector/v2/
- **SSM Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch.html
- **SSM Automation Runbooks** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssa-docs.html
- **Inspector + Security Hub** — https://docs.aws.amazon.com/inspector/latest/user/securityhub-integration.html
- **ECR Image Scanning** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
