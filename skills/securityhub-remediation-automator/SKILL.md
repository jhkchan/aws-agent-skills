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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-expert-knowledge--non-obvious-security-hub-behaviors).
> Eight non-obvious behaviors: Imported-vs-Custom-Action detail-type, batch-update-findings Id+ProductArn, dedup by generator ID, standard enable delay, suppression re-eval, per-account custom actions, EventBridge input transformer, RESOLVED re-open.

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

> Moved to [references/worked-examples.md](references/worked-examples.md#step-6-build-the-lambda-remediation-dispatcher).
> Full Lambda dispatcher reference implementation: RUNBOOK_MAP, start-automation-execution, batch-update-findings NOTIFIED/FAILED notes, SNS fallback.

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

> Moved to [references/worked-examples.md](references/worked-examples.md#literal-output-labels).
> Literal output-label contract restated: FINDING_ID/VERDICT/CHECKLIST/GAP/TEMPLATE block, no prose preface.

### FORBIDDEN — NEVER do these

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#forbidden--never-do-these).
> Seven forbidden patterns: severity filter, deprecated update-findings, suppression expiration, close-after-remediate, SQS DLQ, detail-type confusion, UpdatedAt idempotency.

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

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--review_required-no-runbook-mapped).
> REVIEW_REQUIRED block: custom Lambda credential-exposure finding with no managed runbook, gap and build plan cited.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#anti-patterns--never-do-these-things).
> Anti-pattern catalog: unfiltered EventBridge rules, update-findings, permanent suppression, unclosed findings, missing DLQ, unvalidated standards, detail-type confusion, UpdatedAt keying.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#appendix-a--common-finding-to-runbook-mappings).
> Finding-to-runbook mapping table: FSBP S3.1/S3.4/IAM.3/CloudTrail.1 auto runbooks, CIS 4.1 custom Lambda.

## Appendix B — Decision tree

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#appendix-b--decision-tree).
> Compact decision tree: managed runbook → severity route → verdict; custom-Lambda feasibility branch.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Centralized configuration, cross-region finding aggregation, SSM native finding updates, new-service FSBP controls.

## Expert heuristic: blast radius of auto-remediation

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-blast-radius-of-auto-remediation).
> Pre-production validation protocol: staging deploy with planted findings, 48h dry-run, live enable, production promotion.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Step 0 non-obvious behaviors, FORBIDDEN and Anti-Pattern catalogs, Appendix A runbook mappings, Appendix B compact decision tree, blast-radius validation protocol, recent AWS features
- [worked-examples](references/worked-examples.md) — Step 6 Lambda dispatcher reference implementation, literal output-label contract, REVIEW_REQUIRED worked example
- [eventbridge-finding-patterns](references/eventbridge-finding-patterns.md) — EventBridge rule patterns, severity filters, input transformers, custom-action wiring
- [ssm-runbook-templates](references/ssm-runbook-templates.md) — SSM Automation runbook YAML templates and severity-based SLA table

## Domain

AWS CloudOps / Security Automation — Security Hub-driven remediation.

## AWS documentation

- **AWS Security Hub** — https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html
- **Security Hub Automated Remediation** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-automated-remediation.html
- **Security Hub Custom Actions** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-custom-actions.html
- **BatchUpdateFindings API** — https://docs.aws.amazon.com/securityhub/latest/APIReference/API_BatchUpdateFindings.html
- **Security Hub Insights** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-insights.html
- **Systems Manager Incident Manager** — https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incidents.html
