---
name: inspector2-automation-automator
description: Designs and deploys Amazon Inspector v2 automation workflows — enabling Inspector across EC2, ECR, and Lambda resources; EventBridge routing for finding events; severity-based auto- remediation (Critical = patch via SSM Automation, High = notify with Slack/email); ECR image scan on push integration; Lambda code scan finding handling; finding suppression for accepted risks; Inspector to Security Hub finding forwarding; multi-account via Organizations delegated admin; patch baseline association for OS-level remediation; SSM Automation runbook design for OS patching; container image rebuild trigger via CodeBuild; finding lifecycle (open/suppressed/closed) and SLA enforcement. Emits AUTOMATION_DEPLOYED with a workflow template (CLI or CloudFormation) or REVIEW_REQUIRED with the specific gap. Use when building Inspector-driven remediation, wiring SSM patch baselines to Inspector findings, configuring ECR rescan, or forwarding Inspector findings to Security Hub.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws inspector2 enable, list-findings, list-coverage, aws ssm create-document, start-automation-execution, create-patch-baseline, aws events put-rule, put-targets, aws securityhub batch-import-findings, aws ecr put-image-scanning-configuration, start-image-scan, and aws codebuild start-build — AWS CLI v2, SSO or key-based credentials.
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
  when_to_use: Designing Inspector v2 automation, wiring SSM Automation runbooks to Inspector findings, building severity-based remediation (Critical=patch, High=notify), configuring ECR image scan on push, handling Lambda code scan findings, forwarding Inspector findings to Security Hub, building multi-account Inspector via Organizations delegated admin, configuring patch baseline associations, or suppressing accepted-risk findings.
  activation_triggers: automate Inspector finding, Inspector v2 remediation, ECR image scan on push, Lambda code scan finding, Inspector to Security Hub, severity-based remediation, SSM patch baseline for Inspector, Inspector delegated admin, Inspector finding suppression, container image rebuild, Inspector EventBridge, Critical finding auto-patch
  invocation_schema: 'Input: either (a) an Inspector finding or finding type (e.g., CVE-2026-1234 on i-0abc123, or "all Critical findings in prod-OU"), OR (b) an automation requirement ("auto-patch Critical Inspector findings, notify on High"). Output: deterministic REMEDIATION block per finding class — FINDING/SEVERITY/DETECTION/RESPONSE/SSM_RUNBOOK/VERIFICATION/ VERDICT — where VERDICT is AUTOMATION_DEPLOYED (workflow template ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon Inspector, Inspector v2, Inspector2, vulnerability scanning, ECR image scan, Lambda code scan, EventBridge finding, SSM patch baseline, SSM Automation runbook, Security Hub, delegated admin, finding suppression, finding lifecycle, severity-based remediation, container rebuild, patch remediation
  tags: amazon-inspector, security-automation, ssm-patch, security-hub, eventbridge, automate
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

→ Extended Mindset bullets moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Step-0 expert-knowledge deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Inspector enable + delegated-admin CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ EventBridge rule wiring + triage Lambda handler moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 6: SSM patch baseline for OS findings

→ SSM patch baseline creation CLI + gotchas moved verbatim to [references/ssm-patch-baselines.md](references/ssm-patch-baselines.md).

### Step 7: SSM Automation runbook for patching

→ SSM Automation patch runbook moved verbatim to [references/ssm-patch-baselines.md](references/ssm-patch-baselines.md).

### Step 8: ECR image scan on push + rebuild trigger

→ ECR scan-on-push, rescan, rebuild-trigger implementation moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 9: Lambda code scan finding handling

Lambda findings require function code update — there is no in-place
patch. The workflow:

→ Lambda code-scan finding handler moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Lambda finding gotchas:**
- Code scan findings are NOT auto-remediable via SSM.
- The fix requires the function's CI/CD pipeline to update the
  dependency version.
- Suppression is the only "non-fix" option (Step 11).

### Step 10: Inspector to Security Hub forwarding

→ Security Hub forwarding enable/verify CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Finding suppression CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Suppression rules:**
- Suppressed findings stay in Inspector with `status: SUPPRESSED`.
- They are excluded from default finding queries.
- They re-open if the finding changes (e.g., new evidence).
- Document suppression rationale in `suppressionReason` for audit.

→ Automated suppression Lambda moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 12: Multi-account via delegated admin

→ Multi-account delegated-admin CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ SLA enforcement Lambda moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 14: Patch baseline association to instances

→ Patch-group tagging + baseline association CLI moved verbatim to [references/ssm-patch-baselines.md](references/ssm-patch-baselines.md).

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

→ Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).

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

→ Pre-flight safety checks moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

→ Recent AWS features catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Blast-radius scoping techniques + 3-cycle protocol + CFN pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

**Surface in the output:** for any recommended automation, include
`BLAST_RADIUS: <scope>` (e.g., `OU-wide`,
`tag-scoped:env=prod`, `single-instance`, `single-account`) and
`VALIDATION_STATUS: <scan-non-prod | install-non-prod | scan-prod |
install-prod>`. If `VALIDATION_STATUS` is not `install-prod`, do
NOT mark the auto-patch recommendation as deployable.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example: REVIEW_REQUIRED (missing delegated admin).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — enable/coverage CLI (Steps 2, 12); EventBridge wiring + triage Lambda (Step 5); ECR scan/rescan/rebuild (Step 8); Lambda, Security Hub, suppression and SLA handlers (Steps 9-11, 13); pre-flight safety checks.
- [references/ssm-patch-baselines.md](references/ssm-patch-baselines.md) — extended: patch baseline creation, patch runbooks, patch-group tagging (Steps 6, 7, 14).
- [references/advanced-patterns.md](references/advanced-patterns.md) — extended Mindset bullets; Step-0 expert knowledge; recent AWS features; blast-radius scoping techniques, 3-cycle validation protocol, CloudFormation pattern.

## Domain

AWS CloudOps / Security Automation — Inspector-driven remediation.

## AWS documentation

- **Amazon Inspector** — https://docs.aws.amazon.com/inspector/latest/user/scaling-securing.html
- **Inspector v2 API** — https://docs.aws.amazon.com/inspector/v2/
- **SSM Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch.html
- **SSM Automation Runbooks** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssa-docs.html
- **Inspector + Security Hub** — https://docs.aws.amazon.com/inspector/latest/user/securityhub-integration.html
- **ECR Image Scanning** — https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
