---
name: securityhub-remediation-automator
description: Designs automated remediation workflows for AWS Security Hub findings using EventBridge rules, SSM Automation runbooks, and Lambda remediation functions. Routes findings by severity (Critical/High auto-remediate, Medium/Low notify-only), maps finding types to runbooks or custom Lambda fixers, manages workflow status updates (NEW to NOTIFIED to RESOLVED via batch-update-findings), configures suppression rules with expiration, deploys Security Hub insights for tracking, enables control standards (FSBP, CIS, PCI DSS), integrates with Systems Manager Incident Manager for critical escalation, and orchestrates multi-account remediation via Organizations delegation. Emits AUTOMATION_DEPLOYED or REVIEW_REQUIRED with the specific gap.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws securityhub enable-security-hub, update-standards, create-action-target, batch-update-findings, create-insight, aws events put-rule, put-targets, aws ssm start-automation-execution, aws lambda create-function, and aws cloudformation deploy — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Designing auto-remediation for Security Hub findings, wiring EventBridge custom actions to findings, building severity-based remediation routing (Critical/High auto-fix, Medium/Low notify), enabling compliance standards (CIS, PCI DSS, FSBP) with automated enforcement, configuring suppression rules for accepted risks, deploying Security Hub insights for remediation tracking, or orchestrating multi-account remediation via Organizations delegated administrator.
  activation_triggers: automate Security Hub remediation, Security Hub custom action, EventBridge finding to runbook, severity-based remediation SLA, batch-update-findings workflow status, Security Hub suppression rule, Security Hub insight for tracking, enable CIS PCI FSBP standard, Systems Manager Incident Manager integration, Security Hub multi-account delegation
  invocation_schema: 'Input: either (a) a Security Hub finding type or standard control identifier plus target resource context, OR (b) a remediation requirement. Output: deterministic REMEDIATION block per finding type — FINDING_TYPE/SEVERITY_ROUTE/RUNBOOK/TRIGGER/SAFETY/SUPPRESSION/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (deployment-ready template) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Security Hub, Security Hub remediation, custom action, EventBridge finding, SSM Automation runbook, Lambda remediation, finding severity routing, batch-update-findings, workflow status, suppression rule, Security Hub insight, CIS benchmark, PCI DSS, AWS Foundational Security Best Practices, FSBP, Systems Manager Incident Manager, Organizations delegation, control enablement, compliance standard
  tags: aws-security-hub, security-hub, eventbridge, ssm-automation, lambda-remediation, compliance, automate
---

# Security Hub Remediation Automator

## Mindset

**One-line takeaway:** every Security Hub remediation workflow is a five-stage
pipeline — **detect** (Security Hub control or partner finding) → **route**
(EventBridge rule on severity + finding type) → **decide** (auto-remediate
or notify-only) → **execute** (SSM Automation runbook or Lambda function) →
**close** (update finding workflow status to RESOLVED, verify in insights).
A gap in ANY stage produces either noise (findings pile up with no action)
or silent failure (remediation fires but the finding never closes).

- **Detection** without **routing** is a dashboard nobody watches: Critical
  findings accumulate and operators lose visibility into what matters.
- **Auto-remediation** on Critical/High without a **safety gate** is risky:
  the runbook fires on the first NEW finding, and if the fix is wrong, the
  damage is done before any human reviews it.
- **Finding closure** is the closing gate. A remediation that fixes the
  underlying resource but does NOT update the finding workflow status leaves
  the Security Hub dashboard perpetually dirty, destroying compliance
  reporting accuracy.

## Quick navigation

| You want to... | Go to |
|---|---|
| Route findings by severity to auto-remediate vs notify | Step 3 (severity matrix) |
| Wire a custom action to EventBridge for findings | Step 4 + worked CLI |
| Map a finding type to an SSM runbook or Lambda fixer | Step 5 + Appendix A |
| Build a Lambda remediation function for a custom finding | Step 6 |
| Configure suppression rules for accepted risks | Step 7 |
| Update finding workflow status (NEW to NOTIFIED to RESOLVED) | Step 8 |
| Deploy Security Hub insights for remediation tracking | Step 9 |
| Enable compliance standards (CIS, PCI DSS, FSBP) | Step 10 |
| Integrate with Systems Manager Incident Manager | Step 11 |
| Set up multi-account via Organizations delegation | Step 12 |
| Avoid common remediation pitfalls | Anti-Patterns |
| Recent features (custom actions, insights, control updates) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Security Hub custom actions are NOT automatic.** A custom action
   creates a menu item in the console. It fires ONLY when an operator
   manually selects findings and invokes the action. For automatic
   remediation, you MUST use an EventBridge rule on the finding event
   pattern — NOT the custom action ARN.

2. **`batch-update-findings` is the ONLY API that updates workflow status.**
   `update-findings` is deprecated and operates on a single finding.
   `batch-update-findings` accepts up to 100 finding identifiers per call.
   A remediation that does NOT call it leaves findings in NEW status
   forever, corrupting compliance dashboards.

3. **Security Hub finding events use `detail-type: "Security Hub Findings -
   Imported"`.** NOT "Custom Action". The former fires on ingestion
   (automation). The latter fires on human click (manual). Confusing the
   two is the #1 reason EventBridge-driven remediation does not fire.

4. **Control standards are region-specific.** Enabling CIS, PCI DSS, or
   FSBP in us-east-1 does NOT enable them in eu-west-1. Multi-region
   deployments require per-region `update-standards` calls.

5. **Suppression rules archive findings but do NOT delete them.** A
   suppressed finding has `WorkflowStatus: SUPPRESSED` and
   `RecordState: ARCHIVED`. Always set a `Note` with the acceptance
   rationale and an expiration date for re-evaluation.

## STRICT output contract

Every remediation design MUST produce exactly one REMEDIATION block per
finding type, following this format:

```text
FINDING_ID: <Security Hub finding Id — arn:aws:securityhub:...>
FINDING_TYPE: <Security Hub finding type>
STANDARD: <CIS | PCI | FSBP | Custom | N/A>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] Severity route: CRITICAL_AUTO | HIGH_AUTO | MEDIUM_NOTIFY | LOW_NOTIFY
  [✓|✗] EventBridge rule: <rule name + pattern summary>
  [✓|✗] SSM runbook / Lambda fixer: <document name | function ARN | NONE>
  [✓|✗] batch-update-findings: NOTIFIED on dispatch → RESOLVED on success
  [✓|✗] SQS DLQ: <DLQ ARN on the EventBridge target>
  [✓|✗] Suppression: <NONE | rule + expiration YYYY-MM-DD>
  [✓|✗] Insight: <insight ARN | TBD>
  [✓|✗] Safety gate: <dry-run 48h | pre-prod validated>
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or IaC>
```

## NEVER section

- **NEVER** wire an EventBridge rule on `aws.securityhub` without a
  `Severity.Label` filter. Without it, the rule fires on EVERY finding
  including LOW and INFORMATIONAL, overwhelming Lambda concurrency and
  producing cost spikes.

- **NEVER** use `update-findings` (deprecated). Use
  `batch-update-findings` which accepts up to 100 findings per call and
  is the forward-compatible API.

- **NEVER** suppress a finding without an expiration date in the Note.
  Permanent suppression violates every compliance framework (PCI DSS,
  SOC 2, ISO 27001). Always include "Suppressed until YYYY-MM-DD" and
  build the daily evaluator Lambda to re-open expired suppressions.

- **NEVER** auto-remediate a finding without calling
  `batch-update-findings` afterward. A remediation that fixes the
  resource but leaves the finding in NEW status corrupts dashboards and
  triggers duplicate remediation.

- **NEVER** deploy a Lambda remediation function without an SQS DLQ on
  the EventBridge target. Failed invocations are silently dropped
  without a DLQ; the finding stays open and no one knows.

- **NEVER** enable a compliance standard in production without staging
  validation. Standards generate findings immediately upon enablement.
  An unprepared account can see hundreds of findings in minutes.

- **NEVER** assume Security Hub is enabled in all member accounts. A
  member without Security Hub produces zero findings — not because it
  is secure, but because no controls are running.

- **NEVER** key remediation idempotency on `UpdatedAt`. Security Hub
  re-evaluates controls periodically, changing `UpdatedAt` without
  changing the finding state. Key on finding `Id` for idempotency.

## Expert heuristic

**EventBridge custom action pattern for finding-to-runbook + severity-based
remediation SLA + suppression rule with expiration.**

The highest-leverage Security Hub automation pattern is a three-layer
routing design:

1. **Layer 1 — Severity router (EventBridge rule):** An EventBridge rule
   on `aws.securityhub` filtering on `detail.findings[0].Severity.Label`
   in `["CRITICAL", "HIGH"]` targets a Lambda dispatcher. Critical = 1hr
   SLA; High = 24hr SLA.

2. **Layer 2 — Finding-to-runbook mapper (Lambda dispatcher):** The
   Lambda reads the finding, extracts `Resources[0].Id` and
   `Resources[0].Type`, looks up the SSM runbook in a mapping table, and
   invokes `ssm:start-automation-execution`. For findings without a
   managed runbook, it calls `batch-update-findings` with NOTIFIED and
   sends SNS.

3. **Layer 3 — Suppression with expiration (scheduled Lambda):** A daily
   Lambda checks suppressed findings for expiration. Any suppression
   whose Note date has passed is un-suppressed, re-enabling the finding
   for remediation routing.

**Severity-based remediation SLA table (default):**

| Severity | Auto-remediate | Notify | SLA |
|---|---|---|---|
| CRITICAL | Yes (if runbook + safety gate) | Page on-call | 1 hour |
| HIGH | Yes (if runbook exists) | Email channel | 24 hours |
| MEDIUM | No | Email channel | 7 days |
| LOW | No | Weekly digest | 30 days |

## Configuration dependency graph

```
Security Hub enabled (enable-security-hub)
  +-- Standards enabled (CIS, PCI, FSBP)
  |    +-- Controls generate findings
  |         +-- EventBridge rule (severity-filtered)
  |              +-- Lambda dispatcher (finding to runbook mapping)
  |              |    +-- SSM Automation runbook (managed or custom)
  |              |    +-- batch-update-findings (close finding)
  |              +-- SNS topic (notify security channel)
  |              +-- SQS DLQ (failed remediation buffer)
  |         +-- Suppression evaluator (scheduled Lambda)
  |              +-- batch-update-findings (expire suppressions)
  +-- Organizations delegation (delegated administrator)
  |    +-- Member accounts managed (standards enabled per member, per region)
  +-- Insights (create-insight)
  |    +-- Remediation tracking dashboard
  +-- Incident Manager integration (critical escalation)
       +-- Response plan to on-call escalation
```

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Enabled standards | `get-enabled-standards` | Which control sets are active |
| Active findings | `get-findings` with severity filter | Volume and types to automate |
| Finding types | Finding `Title`, `Resources[0].Type` | Drives runbook selection |
| Custom actions | `describe-action-targets` | Existing manual actions |
| SSM documents | `ssm list-documents --document-type Automation` | Runbook inventory |
| EventBridge rules | `events list-rules` on securityhub bus | Existing automation wiring |
| Delegated admin | `list-organization-admin-accounts` | Multi-account setup state |
| Insights | `get-insights` | Tracking dashboard state |

**If the input is malformed**, emit:

```text
REMEDIATION: <reference>
FINDING_TYPE: UNKNOWN
VERDICT: ERROR
REASON: Cannot design remediation — finding type and resource context required.
GAP: Re-supply get-findings output with Resources[] populated.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Security Hub behaviors

- **Finding events use `detail-type: "Security Hub Findings - Imported"`.**
  NOT "Custom Action". Confusing the two is the most common automation
  failure.

- **`batch-update-findings` requires BOTH `Id` and `ProductArn`.** Missing
  either produces `InvalidInput`.

- **Security Hub deduplicates findings by generator ID + resource.** The
  finding ID stays constant across re-evaluations. Key idempotency on
  finding `Id`, not `UpdatedAt`.

- **Control standards take 5-30 minutes to fully enable.** Wait for
  `STANDARD_REGISTRATION_COMPLETE` before wiring EventBridge rules.

- **Suppressed findings can be un-suppressed by re-evaluation.** If the
  control regenerates with a new finding ID, the old suppression does
  NOT apply. The suppression evaluator must check by generator ID.

- **The delegated administrator cannot create custom actions on behalf
  of members.** Custom actions are per-account. Use CloudFormation
  StackSets for bulk deployment.

- **EventBridge target needs an input transformer.** The finding is
  nested in `detail.findings[0]`. Without a transformer, the Lambda
  receives the full envelope and must parse manually.

- **`WorkflowStatus: RESOLVED` does NOT prevent re-opening.** If the
  control re-evaluates and the resource is still non-compliant, the
  finding re-opens with NEW. Always verify the fix before closing.

### Step 1: Verify Security Hub and standards are active

```bash
aws securityhub get-enabled-standards \
  --query 'StandardsSubscriptions[?StandardsStatus==`ACTIVE`]' --output json
```

If empty:

```bash
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[{"StandardsArn":"arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.4.0"},{"StandardsArn":"arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"}]'
```

### Step 2: Classify findings and map strategy

| Finding type | Standard | Resource | Strategy |
|---|---|---|---|
| FSBP S3.1 | FSBP | `AwsS3Bucket` | Auto-remediate (AWS-DisableS3BucketPublicAccess) |
| FSBP IAM.3 | FSBP | `AwsIamUser` | Auto-remediate (AWS-IAMRevokeUnusedAccessKey) |
| GuardDuty ConsoleLoginWithoutMFA | GuardDuty | `AwsIamUser` | Notify-only (human investigation) |
| CIS 4.1 SG open | CIS | `AwsEc2SecurityGroup` | REVIEW_REQUIRED (custom runbook needed) |

### Step 3: Route by severity (the severity matrix)

| Severity | Finding characteristic | Route | Why |
|---|---|---|---|
| CRITICAL | Credential exposure, root compromise | Auto-remediate + Incident Manager | Breach risk; page on-call |
| HIGH | Public S3, unused keys, disabled trail | Auto-remediate (if runbook exists) | Fixable, reversible; 24hr SLA |
| MEDIUM | Missing tags, minor drift | Notify-only (SNS) | Low blast radius |
| LOW | Informational | Weekly digest | No urgency |
| ACCEPTED RISK | Known exception | Suppress with expiration | Compliant; re-evaluate |

**Decision rule:** default to **notify-only** unless ALL of: (a) managed
runbook or tested Lambda exists, (b) fix is reversible, (c)
post-execution verification configured, (d) `batch-update-findings`
wired to close the finding.

### Step 4: Wire EventBridge rule for automatic remediation

```bash
aws events put-rule \
  --name securityhub-critical-high-auto-remediation \
  --event-pattern '{
    "source": ["aws.securityhub"],
    "detail-type": ["Security Hub Findings - Imported"],
    "detail": {
      "findings": {
        "Severity": {"Label": ["CRITICAL", "HIGH"]},
        "Workflow": {"Status": ["NEW"]}
      }
    }
  }'

aws events put-targets \
  --rule securityhub-critical-high-auto-remediation \
  --targets '[{
    "Id": "remediation-dispatcher",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:securityhub-remediation-dispatcher",
    "InputTransformer": {
      "InputPathsMap": {"finding": "$.detail.findings[0]"},
      "InputTemplate": "{\"finding\": <finding>}"
    },
    "DeadLetterConfig": {"Arn": "arn:aws:sqs:us-east-1:111111111111:securityhub-remediation-dlq"}
  }]'
```

### Step 5: Map finding type to runbook (the dispatch table)

| Finding pattern | SSM runbook | Reversible |
|---|---|---|
| S3 public access | `AWS-DisableS3BucketPublicAccess` | Yes |
| S3 missing encryption | `AWS-EnableS3BucketEncryption` | Yes |
| IAM unused access key | `AWS-IAMRevokeUnusedAccessKey` | Yes |
| CloudTrail disabled | `AWS-EnableCloudTrailLogging` | Yes |
| SG open to world | Custom Lambda | Verify false positives |
| Root compromise | NONE — notify Incident Manager | N/A |

### Step 6: Build the Lambda remediation dispatcher

```python
import boto3
ssm = boto3.client('ssm')
hub = boto3.client('securityhub')
sns = boto3.client('sns')

RUNBOOK_MAP = {
    'S3.1':  {'runbook': 'AWS-DisableS3BucketPublicAccess', 'param': 'S3BucketName'},
    'S3.4':  {'runbook': 'AWS-EnableS3BucketEncryption', 'param': 'S3BucketName'},
    'IAM.3': {'runbook': 'AWS-IAMRevokeUnusedAccessKey', 'param': 'UserName'},
}

def lambda_handler(event, context):
    finding = event['finding']
    fid = finding['Id']
    parn = finding['ProductArn']
    resource = finding['Resources'][0]
    ctrl = finding.get('GeneratorId', '').split('/')[-1]

    if ctrl in RUNBOOK_MAP:
        m = RUNBOOK_MAP[ctrl]
        param_val = resource['Id'].split(':')[-1].split('/')[-1]
        try:
            resp = ssm.start_automation_execution(
                DocumentName=m['runbook'],
                Parameters={m['param']: [param_val],
                    'AutomationAssumeRole': ['arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole']}
            )
            hub.batch_update_findings(
                FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
                Workflow={'Status': 'NOTIFIED'},
                Note={'Text': f'Remediation executed: {resp["AutomationExecutionId"]}', 'UpdatedBy': 'dispatcher'})
            return {'status': 'remediated'}
        except Exception as e:
            hub.batch_update_findings(
                FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
                Note={'Text': f'Remediation FAILED: {e}', 'UpdatedBy': 'dispatcher'})
            raise
    else:
        sns.publish(TopicArn='arn:aws:sns:us-east-1:111111111111:security-alerts',
            Message=f'No auto-remediation for {ctrl}. Manual triage.\nFinding: {fid}')
        hub.batch_update_findings(
            FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
            Workflow={'Status': 'NOTIFIED'},
            Note={'Text': f'No runbook for {ctrl}. Notified.', 'UpdatedBy': 'dispatcher'})
        return {'status': 'notified'}
```

### Step 7: Configure suppression rules for accepted risks

```bash
aws securityhub batch-update-findings \
  --finding-identifiers '[{"Id":"arn:aws:securityhub:us-east-1:111111111111:subscription/cis-finding/abc123","ProductArn":"arn:aws:securityhub:us-east-1::product/aws/securityhub"}]' \
  --workflow '{"Status":"SUPPRESSED"}' \
  --note '{"Text":"Suppressed until 2026-12-01; accepted risk: CI/CD requires port 22. Re-evaluate after VPN migration.","UpdatedBy":"security-team"}' \
  --record-state ARCHIVED
```

### Step 8: Update finding workflow status after remediation

```bash
aws securityhub batch-update-findings \
  --finding-identifiers '[{"Id":"<finding-id>","ProductArn":"<product-arn>"}]' \
  --workflow '{"Status":"RESOLVED"}' \
  --note '{"Text":"Remediation verified: S3 public access disabled. Config confirms COMPLIANT.","UpdatedBy":"verification-lambda"}'
```

### Step 9: Deploy insights for remediation tracking

```bash
aws securityhub create-insight \
  --name "Remediation Backlog by Severity" \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"},{"Value":"HIGH","Comparison":"EQUALS"}],"WorkflowStatus":[{"Value":"NEW","Comparison":"EQUALS"}]}' \
  --group-by-attribute "SeverityLabel"
```

### Step 10: Enable compliance standards

```bash
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[{"StandardsArn":"arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0"},{"StandardsArn":"arn:aws:securityhub:us-east-1::standards/pci-dss/v/1.0.0"}]'
```

### Step 11: Integrate with Incident Manager

For CRITICAL findings requiring human escalation:

```bash
aws ssm-incidents create-response-plan \
  --name securityhub-critical-escalation \
  --incident-template '{"title":"Security Hub Critical Finding","impact":1,"severity":1}'
```

Wire an EventBridge rule on CRITICAL findings to trigger the response plan.

### Step 12: Multi-account via Organizations delegation

```bash
aws securityhub enable-organization-admin-account --admin-account-id 222222222222
aws securityhub create-members \
  --account-details '[{"AccountId":"333333333333","Email":"secops@example.com"}]'
```

## Output format

### Literal output labels

Every remediation design MUST emit exactly one block per finding type using
the labels `FINDING_ID:`, `FINDING_TYPE:`, `VERDICT:`, `CHECKLIST:`, `GAP:`,
and `TEMPLATE:`. Do NOT preface with prose.

```text
FINDING_ID: <finding Id — arn:aws:securityhub:us-east-1:ACCT:subscription/...>
FINDING_TYPE: <Security Hub finding type>
STANDARD: <CIS | PCI | FSBP | Custom | N/A>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] Severity route: CRITICAL_AUTO | HIGH_AUTO | MEDIUM_NOTIFY | LOW_NOTIFY
  [✓|✗] EventBridge rule: <rule name + pattern>
  [✓|✗] SSM runbook / Lambda fixer: <name | ARN | NONE>
  [✓|✗] batch-update-findings: wired
  [✓|✗] SQS DLQ: <ARN>
  [✓|✗] Suppression: <NONE | rule+expiration>
  [✓|✗] Insight: <ARN | TBD>
  [✓|✗] Safety gate: <validated>
GAP: <specific missing piece or None>
TEMPLATE: <CLI snippet or IaC>
```

### FORBIDDEN — NEVER do these

1. NEVER wire an EventBridge rule on `aws.securityhub` without a
   `Severity.Label` filter. Without it the rule fires on EVERY finding
   including LOW and INFORMATIONAL, overwhelming Lambda concurrency and
   spiking costs.

2. NEVER use `update-findings` (deprecated). Use `batch-update-findings`
   which accepts up to 100 findings per call and is the forward-compatible
   API.

3. NEVER suppress a finding without an expiration date in the Note.
   Permanent suppression violates PCI DSS, SOC 2, ISO 27001. Always set
   "Suppressed until YYYY-MM-DD" and run a daily evaluator Lambda.

4. NEVER auto-remediate without calling `batch-update-findings` afterward.
   A remediation that fixes the resource but leaves the finding in NEW
   status triggers duplicate remediation and corrupts dashboards.

5. NEVER deploy a Lambda remediation function without an SQS DLQ on the
   EventBridge target. Failed invocations are silently dropped without a
   DLQ; the finding stays open and no one knows.

6. NEVER confuse `detail-type: "Security Hub Findings - Imported"` with
   `"Security Hub Findings - Custom Action"`. The former is for
   automation (fires on ingestion); the latter fires on human console
   click.

7. NEVER key remediation idempotency on `UpdatedAt`. Security Hub
   re-evaluates controls periodically, changing `UpdatedAt` without
   changing the finding state. Key on finding `Id`.

### Worked example — Critical S3 public-access finding, auto-remediated

Scenario: FSBP control S3.1 detects a publicly accessible S3 bucket.
EventBridge routes the CRITICAL finding to a Lambda dispatcher that
invokes the `AWS-DisableS3BucketPublicAccess` SSM runbook, then closes
the finding via `batch-update-findings`.

```text
FINDING_ID: arn:aws:securityhub:us-east-1:111111111111:subscription/cis-aws-foundations-benchmark/v/1.2.0/3.1/finding/01a23456-7890-abcd-ef01-234567890abc
FINDING_TYPE: Software and Configuration Checks/AWS Security Best Practices/S3.1
STANDARD: FSBP
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [✓] Severity route: CRITICAL_AUTO (Critical → SSM auto-remediate, 1h SLA)
  [✓] EventBridge rule: securityhub-critical-auto-remediation
      pattern: {"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"],"detail":{"findings":{"Severity":{"Label":["CRITICAL"]},"Workflow":{"Status":["NEW"]}}}}
  [✓] SSM runbook: AWS-DisableS3BucketPublicAccess (param: S3BucketName = corp-data-lake-prod)
  [✓] batch-update-findings: NOTIFIED on dispatch → RESOLVED after runbook success
  [✓] SQS DLQ: arn:aws:sqs:us-east-1:111111111111:securityhub-remediation-dlq
  [✓] Suppression: NONE
  [✓] Insight: arn:aws:securityhub:us-east-1:111111111111:insight/abc123
  [✓] Safety gate: dry-run tested 48h in staging, zero false positives
GAP: None
TEMPLATE:
  aws events put-rule --name securityhub-critical-auto-remediation \\
    --event-pattern '{"source":["aws.securityhub"],"detail-type":["Security Hub Findings - Imported"],"detail":{"findings":{"Severity":{"Label":["CRITICAL"]},"Workflow":{"Status":["NEW"]}}}}'
  aws ssm start-automation-execution \\
    --document-name AWS-DisableS3BucketPublicAccess \\
    --parameters '{"S3BucketName":["corp-data-lake-prod"],"AutomationAssumeRole":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}'
  aws securityhub batch-update-findings \\
    --finding-identifiers '[{"Id":"arn:aws:securityhub:us-east-1:111111111111:subscription/cis-aws-foundations-benchmark/v/1.2.0/3.1/finding/01a23456-7890-abcd-ef01-234567890abc","ProductArn":"arn:aws:securityhub:us-east-1::product/aws/securityhub"}]' \\
    --workflow '{"Status":"RESOLVED"}' \\
    --note '{"Text":"S3 public access disabled via AWS-DisableS3BucketPublicAccess. Verified BlockPublicAccess=TRUE.","UpdatedBy":"remediation-dispatcher"}'
```

Severity routing summary (how each tier is handled):

| Severity | Route | Mechanism | SLA |
|---|---|---|---|
| CRITICAL | SSM auto-remediate | EventBridge → Lambda dispatcher → SSM runbook → batch-update-findings RESOLVED | 1 hour |
| HIGH | Lambda fixer | EventBridge → Lambda custom remediation → batch-update-findings RESOLVED | 24 hours |
| MEDIUM | Notify only | EventBridge → SNS → security channel email | 7 days |
| LOW | Weekly digest | Scheduled Lambda → aggregated SNS digest | 30 days |

### Worked example — REVIEW_REQUIRED, no runbook mapped

```text
FINDING_ID: arn:aws:securityhub:us-east-1:111111111111:subscription/custom/lambda-cred-exposure/finding/02b34567
FINDING_TYPE: Software and Configuration Checks/Custom/ExposedCredentialsInLambda
STANDARD: Custom
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [✗] Severity route: HIGH_AUTO — no runbook available
  [✓] EventBridge rule: securityhub-high-auto-remediation (configured)
  [✗] SSM runbook / Lambda fixer: NONE — no managed runbook for Lambda env-var credential exposure
  [✓] batch-update-findings: NOTIFIED (SNS to security channel)
  [✓] SQS DLQ: arn:aws:sqs:us-east-1:111111111111:securityhub-remediation-dlq
  [✓] Suppression: NONE
  [✗] Insight: TBD — create insight for tracking
  [✗] Safety gate: not yet built
GAP: No managed runbook exists. Build a custom Lambda that (1) reads the finding, (2) rotates the credential via Secrets Manager, (3) updates the environment variable, (4) calls batch-update-findings RESOLVED. Then wire the EventBridge rule.
TEMPLATE: (custom Lambda — see Step 6 pattern in skill body)
```

### Decision tree

```text
Is there a managed SSM runbook for this finding type?
├─ Yes → Severity CRITICAL or HIGH?
│        ├─ Yes → AUTOMATION_DEPLOYED
│        │        (EventBridge → Lambda dispatcher → SSM runbook → batch-update-findings RESOLVED)
│        └─ No (MEDIUM/LOW) → MEDIUM_NOTIFY / LOW_NOTIFY
│                         (EventBridge → SNS → email/digest, no auto-fix)
└─ No → Is a custom Lambda remediation feasible?
         ├─ Yes → Build + test in staging → AUTOMATION_DEPLOYED
         └─ No → REVIEW_REQUIRED (cite the gap: "no runbook, Lambda not feasible")
                  (route: NOTIFIED via SNS, create insight for backlog tracking)

Is the finding an accepted risk?
  → Suppress with expiration date in Note → daily evaluator re-opens when expired
```

## Anti-Patterns — NEVER do these things

- NEVER wire an EventBridge rule on `aws.securityhub` without a
  `Severity.Label` filter. The rule fires on EVERY finding, including
  LOW, producing cost spikes and Lambda concurrency exhaustion.

- NEVER use `update-findings` (deprecated). Use `batch-update-findings`
  for all workflow status changes. The old API is single-finding and
  does not support batch updates.

- NEVER suppress a finding without an expiration date. Permanent
  suppression violates PCI DSS, SOC 2, ISO 27001. Always include
  "Suppressed until YYYY-MM-DD" and run the daily evaluator Lambda.

- NEVER auto-remediate without calling `batch-update-findings`
  afterward. A remediation that fixes the resource but leaves the
  finding in NEW status triggers duplicate remediation.

- NEVER deploy a Lambda remediation function without an SQS DLQ on
  the EventBridge target. Failed invocations are silently dropped.

- NEVER enable a compliance standard in production without staging
  validation. Standards generate findings immediately — hundreds in
  minutes in an unprepared account.

- NEVER confuse `detail-type: "Security Hub Findings - Imported"`
  with `"Security Hub Findings - Custom Action"`. The former is for
  automation; the latter fires on human console click.

- NEVER key idempotency on `UpdatedAt`. Security Hub re-evaluates
  periodically, changing `UpdatedAt` without changing state. Key on
  finding `Id` for deduplication.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for finding <type> in account
  <account>. Proceed? (yes/no)`

- **Back up current configuration:** `aws securityhub get-enabled-standards
  > /tmp/securityhub-baseline-$(date +%s).json`

- **Before enabling auto-remediation on a new finding type**, test the
  Lambda dispatcher with a sample finding payload and verify it produces
  correct SSM execution parameters.

## Appendix A — Common finding-to-runbook mappings

| Standard | Control | Finding type | Runbook | Strategy |
|---|---|---|---|---|
| FSBP | S3.1 | S3 public access | `AWS-DisableS3BucketPublicAccess` | Auto |
| FSBP | S3.4 | S3 missing encryption | `AWS-EnableS3BucketEncryption` | Auto |
| FSBP | IAM.3 | IAM unused key | `AWS-IAMRevokeUnusedAccessKey` | Auto (caveat) |
| FSBP | CloudTrail.1 | Trail disabled | `AWS-EnableCloudTrailLogging` | Auto |
| CIS | 4.1 | SG open to 0.0.0.0/0 | Custom Lambda | REVIEW_REQUIRED |

## Appendix B — Decision tree

```
Managed SSM runbook for the finding type?
+-- Yes -> Severity CRITICAL or HIGH?
|         +-- Yes -> AUTOMATION_DEPLOYED
|         +-- No  -> MEDIUM_NOTIFY or LOW_NOTIFY
+-- No  -> Custom Lambda feasible?
          +-- Yes -> Build + test -> AUTOMATION_DEPLOYED
          +-- No  -> REVIEW_REQUIRED (gap cited)
```

## Recent AWS features (2024-2026)

- **Security Hub centralized configuration (2024):** Delegated admin can
  push policies and control enablements across all members centrally.
- **Finding aggregation across regions (2024-2025):** Single region
  aggregates findings from all enabled regions, simplifying rule design.
- **SSM runbook native finding updates (2025):** SSM `aws:updateSecurityHubFinding`
  action eliminates the need for a separate Lambda to close findings.
- **Controls for new services (2025-2026):** FSBP controls for Amazon Q,
  Bedrock, and GenAI services. Remediation runbooks shipping incrementally.

## Expert heuristic: blast radius of auto-remediation

> ALWAYS validate the EventBridge severity filter and Lambda dispatch
> table in a non-production account first. Deploy with a dry-run flag
> in the Lambda for 48 hours: log what it WOULD do without calling SSM.
> Then enable live execution after verifying zero false positives.

**Pre-production validation protocol:**

1. Deploy EventBridge rule + Lambda in staging. Plant 5 deliberate findings.
2. Run Lambda in dry-run mode 48 hours. Verify mapping correctness.
3. Enable live execution. Verify all 5 remediated AND closed via
   `batch-update-findings`.
4. Promote to production with severity filter active.

## Domain

AWS CloudOps / Security Automation — Security Hub-driven remediation.

## AWS documentation

- **AWS Security Hub** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
- **Security Hub Automated Remediation** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-automated-remediation.html
- **Security Hub Custom Actions** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-custom-actions.html
- **BatchUpdateFindings API** — https://docs.aws.amazon.com/securityhub/latest/APIReference/API_BatchUpdateFindings.html
- **Security Hub Insights** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-insights.html
- **Systems Manager Incident Manager** — https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incidents.html
