---
name: config-rule-compliance-automator
description: Designs and deploys AWS Config rule compliance automation across an AWS estate. Selects from 80+ managed rules or designs custom Lambda rules, wires SSM Automation remediation with trigger semantics, deploys conformance packs for CIS/PCI/NIST via CloudFormation StackSets, configures multi-account visibility via Config Aggregator, implements organizational config rules, deploys custom policy rules (Git-based via CodeCommit), sets up SNS compliance notifications, and detects configuration drift. Emits AUTOMATION_DEPLOYED or REVIEW_REQUIRED.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline compliance-design. Live deployment uses aws configservice put-config-rule, put-remediation-configurations, put-conformance-pack, describe-configuration-aggregators, aws ssm create-document, start-automation-execution, aws cloudformation create-stack-set — AWS CLI v2, SSO or key-based credentials.
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
  when_to_use: Designing Config rule compliance automation, selecting managed rules for a compliance framework, building custom Lambda rules, deploying conformance packs via StackSets, wiring SSM remediation to compliance findings, configuring Config Aggregator for multi-account visibility, implementing organizational config rules, or detecting configuration drift.
  activation_triggers: automate Config compliance, managed vs custom Config rule, conformance pack deployment, CIS benchmark Config rules, PCI-DSS Config rules, NIST 800-53 Config rules, SSM remediation for Config, Config Aggregator multi-account, organizational config rule, custom policy rule CodeCommit, compliance dashboard, drift detection Config, StackSets conformance pack
  invocation_schema: 'Input: either (a) a compliance framework or set of requirements plus the target accounts/regions, OR (b) an existing Config setup to audit. Output: deterministic COMPLIANCE block per rule set — RULES/ REMEDIATION/FRAMEWORK/AGGREGATOR/VERDICT.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Config, Config rules, managed rules, custom Lambda rules, conformance packs, CIS benchmark, PCI-DSS, NIST 800-53, SSM Automation remediation, Config Aggregator, organizational config rules, custom policy rules, compliance dashboard, drift detection, StackSets, governance automation
  tags: aws-config, conformance-packs, ssm-automation, cis, compliance, governance, automate
---

# Config Rule Compliance Automator

## Mindset

**One-line takeaway:** every Config compliance automation is a five-stage
pipeline — **select** (managed vs custom rule) → **deploy** (conformance
pack via StackSets) → **remediate** (SSM Automation with trigger
semantics) → **aggregate** (Config Aggregator for multi-account
visibility) → **monitor** (compliance dashboard + SNS + drift detection).
A gap in ANY stage produces a false sense of compliance.

- **Rule selection** without understanding the managed-rule coverage gap
  produces a baseline that looks complete but misses custom requirements.
  80+ managed rules cover ~70% of CIS controls; the rest need custom
  rules.
- **Deployment** without StackSets means manual per-account replication.
  A conformance pack deployed to one account is not a compliance program.
- **Remediation** without trigger semantics (automatic vs manual) is
  either dangerous or useless — auto-fixing a false positive or leaving
  findings NON_COMPLIANT forever.

## Quick navigation

| You want to... | Go to |
|---|---|
| Select managed rules for a framework | Step 1 + Appendix A |
| Decide managed vs custom rule | Step 2 (selection criteria) |
| Build a custom Lambda rule | Step 3 |
| Deploy conformance packs via StackSets | Step 4 |
| Wire SSM remediation to compliance findings | Step 5 |
| Deploy CIS / PCI / NIST conformance pack | Step 6 |
| Configure Config Aggregator for multi-account | Step 7 |
| Implement organizational config rules | Step 8 |
| Deploy custom policy rules via CodeCommit | Step 9 |
| Set up SNS compliance notifications | Step 10 |
| Build a compliance dashboard | Step 11 |
| Detect configuration drift | Step 12 |
| Avoid common compliance pitfalls | Anti-Patterns |
| Recent features (org rules, drift) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Managed rules are region-specific.** A rule in `us-east-1` does NOT
   evaluate resources in `eu-west-1`. For multi-region compliance, deploy
   via StackSets covering all active regions.

2. **`put-config-rule` is idempotent on `ConfigRuleName`.** Re-calling
   overwrites atomically with no version history. Always capture current
   state (`describe-config-rules`) before modifying.

3. **SSM remediation via `put-remediation-configurations` does NOT fire
   on existing NON_COMPLIANT resources.** It only fires on NEW
   evaluations. To remediate the backlog, call
   `start-remediation-execution` per resource.

4. **Conformance pack deployment via StackSets requires
   `CAPABILITY_IAM`.** The pack creates Config rules, SSM documents, and
   IAM roles. Without `--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM`
   the StackSet silently fails on role creation.

5. **Config Aggregator does NOT remediate.** It provides VISIBILITY only.
   To remediate across accounts, deploy remediation configurations per
   account via StackSets.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Config recorder status | `describe-configuration-recorders` | Rules can't evaluate without a recorder |
| Existing Config rules | `describe-config-rules` | Avoid duplicate rules |
| Existing conformance packs | `describe-conformance-packs` | Check framework coverage |
| Config Aggregator status | `describe-configuration-aggregators` | Multi-account visibility |
| Organizations integration | `organizations describe-organization` | Org rules require integration |
| Target compliance framework | CIS / PCI / NIST / custom | Drives rule selection |
| StackSet status | `cloudformation list-stack-sets` | Multi-account deployment vehicle |

**If the input is malformed** (no recorder, no framework), emit:

```text
COMPLIANCE: <reference>
RULE: <rule-name>
VERDICT: ERROR
REASON: Cannot design compliance — Config recorder and target framework required.
GAP: Enable Config recorder and specify the compliance framework.
```

## Configuration dependency graph

```
Config Recorder (per account, per region)
  │
  ├── Managed Config Rules (80+ AWS-managed)
  │     └── Remediation Configurations → SSM Automation
  │
  ├── Custom Config Rules (Lambda or Guard custom policy)
  │     └── Remediation Configurations → SSM Automation
  │
  ├── Conformance Pack (CloudFormation template)
  │     ├── Rules + Remediation + SNS + IAM roles
  │     └── Deployed via StackSets (multi-account, multi-region)
  │
  ├── Organizational Config Rules (org-level, auto-propagated)
  │
  ├── Config Aggregator (multi-account VISIBILITY only)
  │     └── Compliance dashboard (cross-account view)
  │
  ├── SNS Compliance Notifications (per severity)
  │
  └── Drift Detection (CloudFormation drift + Config timeline)
```

## Process — Compliance automation design (apply in order)

### Step 0: Expert knowledge — non-obvious Config behaviors

Step 0 expert knowledge (dead-rule scope mismatch, periodic-rule cadence, Lambda timeout/memory, remediation TargetId name-vs-ARN, org-rule service-linked role, StackSet auto-deployment) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before designing the rule set.

### Step 1: Managed rule selection for a framework

For CIS AWS Foundations Benchmark, the managed rule coverage map:

| CIS Control | Managed rule | Coverage |
|---|---|---|
| 1.1 Avoid root access keys | `iam-root-access-key-check` | Full |
| 1.2 MFA on root | `root-account-mfa-enabled` | Full |
| 1.4 IAM password policy | `iam-password-policy` | Full |
| 1.13 Trail exists | `cloudtrail-enabled` | Full |
| 1.14 S3 bucket access logging | `s3-bucket-logging-enabled` | Full |
| 2.1 SG default restrict | Custom needed | **Gap** |
| 2.2-2.9 Security groups | `vpc-sg-open-only-to-authorized-ports` | Partial |
| 3.1-3.4 CloudTrail config | `cloudtrail-enabled`, `multi-region-cloudtrail-enabled` | Full |
| 4.1-4.4 Monitoring | `cloudwatch-alarm-action-check`, `config-enabled` | Partial |

**Coverage gap rule:** for any CIS control without full managed coverage,
a custom Lambda or custom policy rule is required. Mark these as
`CUSTOM_RULE_REQUIRED`.

### Step 2: Managed vs custom rule selection criteria

| Criterion | Managed | Custom Policy (Guard) | Custom Lambda |
|---|---|---|---|
| Single-resource boolean check | YES | Yes | Only if complex |
| Multi-resource correlation | No | No | YES |
| External data lookup | No | No | YES |
| Cost sensitivity | Free | Free | Lambda charges |
| Maintenance burden | Zero | Low | High |

**Decision rule:** ALWAYS prefer managed rules when they exist (80+,
AWS-maintained, no Lambda cost). Use custom policy rules (Guard 2,
server-side) for logic expressible as policy. Use custom Lambda only
when the logic exceeds both.

### Step 3: Build a custom Lambda rule

Step 3 custom-Lambda rule (full Python evaluator and `put-config-rule` deploy CLI) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when a CIS gap needs a custom rule.

### Step 4: Deploy conformance packs via StackSets

Step 4 StackSet deployment CLI (create-stack-set with CAPABILITY_IAM + SERVICE_MANAGED auto-deployment, stack instances, verification) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when deploying the baseline.

### Step 5: Wire SSM remediation to compliance findings

```bash
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "s3-bucket-server-side-encryption-enabled",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-EnableS3BucketEncryption",
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 600,
    "Parameters": {
      "S3BucketName": {"ResourceValue": {"Value": "RESOURCE_ID"}},
      "AutomationAssumeRole": {"StaticValue": {"Values": ["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}
    }
  }]'
```

| Fix type | Trigger | Why |
|---|---|---|
| Reversible, low blast radius (S3 encryption) | **Automatic** | Risk of inaction > risk of action |
| Destructive (SG revoke, IAM detach) | **Manual** | False-positive risk |
| Multi-step (terminate, revoke credential) | **Manual via Change Manager** | Application impact |

### Step 6: Deploy framework conformance packs

Step 6 CIS conformance-pack sample YAML (rules + RemediationConfiguration + SNS topic) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when authoring the pack template.

### Step 7: Config Aggregator for multi-account visibility

Step 7 Config Aggregator CLI (org aggregator + cross-account NON_COMPLIANT query; aggregator = visibility only) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when configuring multi-account visibility.

### Step 8: Organizational config rules

Step 8 organizational config rules CLI (enable service access, org rule + org remediation configuration) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for org-level deployment.

### Step 9: Custom policy rules (Git-based via CodeCommit)

Step 9 custom policy rule CLI (Guard 2 DSL, server-side evaluation, no Lambda cost) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for policy-expressible checks.

### Step 10: SNS compliance notifications

Step 10 SNS compliance-notification Lambda (Python publisher) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when wiring notifications.

### Step 11: Compliance dashboard

Step 11 compliance-dashboard CLI (CloudWatch put-dashboard with per-rule NON_COMPLIANT metrics) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when building the dashboard.

### Step 12: Drift detection

Step 12 drift-detection CLI (CloudFormation drift, Config timeline, EventBridge alert rule) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when detecting drift.

## Output format (STRICT output contract)

```text
COMPLIANCE: <reference>
FRAMEWORK: <CIS | PCI-DSS | NIST-800-53 | custom>
RULES:
  - Managed: <list>
  - Custom: <list + gap rationale>
  - Custom Policy (Guard): <list>
REMEDIATION:
  - Automatic: <rule → SSM document pairs>
  - Manual: <rule → SSM document pairs with rationale>
AGGREGATOR:
  - Status: configured | not configured
  - Scope: <accounts and regions>
FRAMEWORK_DEPLOYMENT:
  - Method: StackSet | put-conformance-pack | org rule
  - Auto-deployment: enabled | disabled
  - Regions: <list>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or IaC>
```

### Worked example — AUTOMATION_DEPLOYED, CIS S3 encryption

```text
COMPLIANCE: cis-s3-encryption-baseline
FRAMEWORK: CIS AWS Foundations Benchmark (2.1, 2.2)
RULES:
  - Managed: s3-bucket-server-side-encryption-enabled, s3-bucket-versioning-enabled
  - Custom: none required
  - Custom Policy (Guard): none
REMEDIATION:
  - Automatic: s3-bucket-server-side-encryption-enabled → AWS-EnableS3BucketEncryption
  - Automatic: s3-bucket-versioning-enabled → AWS-EnableS3BucketVersioning
AGGREGATOR:
  - Status: configured
  - Scope: org-wide, all active regions
FRAMEWORK_DEPLOYMENT:
  - Method: StackSet (cis-compliance-baseline)
  - Auto-deployment: enabled
  - Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"s3-bucket-server-side-encryption-enabled","TargetType":"SSM_DOCUMENT","TargetId":"AWS-EnableS3BucketEncryption","Automatic":true,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"S3BucketName":{"ResourceValue":{"Value":"RESOURCE_ID"}},"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}}}]'
```

### Worked example — REVIEW_REQUIRED, Aggregator missing

Worked example — REVIEW_REQUIRED, Aggregator missing (failure-mode output shape) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the REVIEW_REQUIRED output shape.

## Anti-Patterns — NEVER do these things

- NEVER deploy Config rules to a single region and assume global
  compliance. Config rules are region-scoped. An S3 bucket in
  `eu-west-1` is NOT evaluated by a rule in `us-east-1`. Deploy via
  StackSets with all active regions.

- NEVER wire `Automatic: true` remediation to a custom Lambda rule
  without testing the rule's false-positive rate first. A logic bug
  marks compliant resources as NON_COMPLIANT, and the automatic
  remediation "fixes" resources that were already correct.

- NEVER assume a conformance pack in `CREATE_COMPLETE` includes
  remediation. The default is rules-only. Remediation must be an
  explicit `AWS::Config::RemediationConfiguration` resource in the pack.
  Verify with `describe-remediation-configurations`.

- NEVER deploy a conformance pack via StackSets without
  `CAPABILITY_IAM`. The pack creates IAM roles for Config and SSM.
  Without IAM capabilities, role creation silently fails — rules deploy
  but remediation does not.

- NEVER omit `MaximumAutomaticAttempts` on remediation. The default is
  1 attempt. A transient SSM failure produces a permanently
  unremediated resource.

- NEVER forget to remediate the existing NON_COMPLIANT backlog.
  `Automatic: true` fires only on NEW evaluations. Resources already
  NON_COMPLIANT remain so until you call `start-remediation-execution`.

- NEVER assume the Config Aggregator can remediate. It provides
  VISIBILITY only. An aggregator without per-account remediation is a
  dashboard, not a compliance program.

- NEVER use a custom Lambda rule without raising memory above 256MB for
  multi-API rules. A timeout produces "ERROR" not "NON_COMPLIANT" — the
  rule looks broken, not the resource.

- NEVER deploy organizational config rules without the
  `AWSServiceRoleForConfig` service-linked role. Without it,
  `put-organization-config-rule` returns `AccessDenied`.

- NEVER disable StackSet auto-deployment for ongoing compliance. New
  accounts added to the OU do NOT receive the conformance pack. Always
  enable auto-deployment for compliance baselines.

- NEVER scope a Config rule to a resource type NOT in the recorder's
  recording group. The rule will never emit NON_COMPLIANT. This is the
  most common cause of "compliant by absence."

- NEVER confuse `describe-config-rules` compliance status with actual
  resource compliance. Use `get-compliance-summary-by-config-rule` for
  actual COMPLIANT/NON_COMPLIANT counts.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for framework <framework> in
  account <account>. Proceed? (yes/no)`

- **Verify the Config recorder is active.** Rules cannot evaluate
  without a recorder.

- **Back up existing rules before modifying.** Config rules have no
  version history. `describe-config-rules > backup.json`.

- **For conformance pack deployment, dry-run the template.**
  `aws cloudformation validate-template --template-body file://pack.yaml`.

- **For organizational rules, verify org integration.**
  `aws organizations describe-organization`.

## Appendix A — Managed rules by framework

Appendix A managed-rules-by-framework coverage table (~90% CIS IAM, ~70% CIS networking, ~100% CIS logging, PCI-DSS, NIST 800-53) moved verbatim to [references/managed-rules-and-frameworks.md](references/managed-rules-and-frameworks.md).
Load on demand when selecting rules for a framework.

## Appendix B — Decision tree

```
Is there a managed rule for the check?
├─ Yes → Scope recorded by recorder?
│       ├─ Yes → Deploy managed rule + remediation
│       └─ No  → Add type to recorder first
└─ No  → Logic expressible in Guard (custom policy)?
        ├─ Yes → Deploy custom policy rule (no Lambda cost)
        └─ No  → Deploy custom Lambda rule
                Test false-positive rate before automatic remediation
```

## Recent AWS features (2024-2026)

Recent AWS features (org rules GA, Guard 2 custom policy rules, drift enhancements, selective aggregation, OU auto-deployment, template builder) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing recent setups.

## Expert heuristic: managed vs custom rule selection criteria + SSM remediation document lifecycle + conformance pack deployment via StackSets

Expert heuristic deep dive (managed-vs-custom selection rule, SSM remediation document lifecycle, conformance-pack deployment checklist, MANAGED_RULE_COUNT / CUSTOM_RULE_COUNT / AUTO_DEPLOYMENT / REGION_COVERAGE output fields) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before finalizing the design.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — Steps 3/4/6 full CLI payloads and the REVIEW_REQUIRED worked example moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, Steps 7-12 recipes (aggregator, org rules, Guard 2 policy rules, SNS, dashboard, drift), Recent AWS features, and the expert heuristic moved from SKILL.md.
- [references/managed-rules-and-frameworks.md](references/managed-rules-and-frameworks.md) — now also holds the Appendix A framework coverage table moved from SKILL.md.

## Domain

AWS CloudOps / Governance Automation — Config rule compliance automation.

## AWS documentation

- **AWS Config Rules** — https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config-rules.html
- **AWS Config Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **Config Aggregator** — https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html
- **Organizational Config Rules** — https://docs.aws.amazon.com/config/latest/developerguide/organization-config-rules-overview.html
- **SSM Automation** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssa-docs.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
