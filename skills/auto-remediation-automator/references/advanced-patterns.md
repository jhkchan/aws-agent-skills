# Auto-Remediation Automator — Advanced Patterns

Expert-knowledge deep dives, alternative patterns, edge cases, and
recent-feature notes moved from SKILL.md. Load on demand.


## Step 0: Expert knowledge — non-obvious Config + SSM behaviors (moved from SKILL.md)

These behaviors change the workflow design if ignored:

- **`put-remediation-configurations` accepts a `TargetId` for org-level
  rules.** When the Config rule is deployed via an organization
  conformance pack, the remediation must be configured at the org
  level (`TargetType: AWS_ACCOUNT`) — member-account-level remediation
  configurations are ignored for org-deployed rules.

- **`Automatic: true` remediation does NOT fire on existing NON_COMPLIANT
  resources.** It only fires on NEW NON_COMPLIANT evaluations. To
  remediate the existing backlog, you must explicitly call
  `start-remediation-execution` per resource. This is the most common
  "I configured remediation and nothing happened" issue.

- **SSM Automation execution role is a service role, NOT the caller's
  role.** Config assumes a role to invoke SSM; SSM assumes a role to
  execute the runbook. Two service roles, both pre-provisioned. A
  single `AssumeRole` chain failure produces `ACCESS_DENIED` deep in
  the execution history.

- **The SSM document `Outputs` are NOT visible in the Config timeline.**
  Config records resource state changes (NON_COMPLIANT → COMPLIANT).
  SSM records runbook execution status (Success/Failed). To
  reconstruct what happened, you must join the two via timestamps in
  CloudTrail — there is no native join.

- **`AWS-Config-*` and `AWS-*` SSM documents are AWS-managed and
  versioned by AWS.** You cannot edit them. When AWS ships a new
  version, the remediation configuration automatically picks it up
  unless you pinned a specific version in `DocumentVersion`. Pinning
  is safer for stability; floating is better for bug fixes.

- **A Config rule scoped to a resource type that is NOT recorded by
  the recorder will never emit NON_COMPLIANT.** Remediation wired to
  such a rule is dead configuration. Always verify the recorder scope
  includes the rule's target resource type before wiring remediation.

- **`start-remediation-execution` is synchronous API but asynchronous
  execution.** The API returns immediately with an `ExecutionId`. The
  runbook continues executing for seconds to minutes. Poll
  `describe-remediation-execution-status` for completion.

- **SSM Automation step failures do NOT roll back.** Each step is
  independent. A multi-step runbook that fails on step 3 of 5 leaves
  steps 1-2 applied. Custom runbooks must include explicit rollback
  steps (`onFailure: abort` is the default, but earlier mutations
  persist).

- **EventBridge-driven remediation (Config state-change → Lambda) is
  not deduplicated.** Config emits a state-change event on every
  evaluation transition. A flapping resource (NON_COMPLIANT →
  COMPLIANT → NON_COMPLIANT) triggers the Lambda on every transition.
  Idempotency is the consumer's responsibility.

- **Conformance-pack `RemediationConfiguration` blocks use the SSM
  document name, not ARN.** A typo in the document name produces a
  silent deployment failure (the pack reports CREATE_COMPLETE but the
  remediation is not wired).


## EventBridge alternative patterns (moved from SKILL.md Step 7)

EventBridge rule pattern:

```bash
aws events put-rule \
  --name config-remediation-custom \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Configuration Item Change"],
    "detail": {
      "configurationItem": {
        "configurationItemStatus": ["OK"],
        "resourceType": ["AWS::S3::Bucket"],
        "complianceType": ["NON_COMPLIANT"]
      }
    }
  }'
```

Or simpler, on compliance change:

```bash
aws events put-rule \
  --name config-compliance-change \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Rules Compliance Changed"],
    "detail": {"newEvaluationResult": {"complianceType": ["NON_COMPLIANT"]}}
  }'
```

Add the Lambda target with DLQ:

```bash
aws events put-targets \
  --rule config-compliance-change \
  --targets '[{"Id":"custom-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:custom-remediation","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:config-remediation-dlq"}}]'
```


## Conformance-pack bulk remediation sample (moved from SKILL.md Step 8)

```yaml
Resources:
  S3PublicReadProhibitedRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: s3-bucket-public-read-prohibited
      Source:
        Owner: AWS
        SourceIdentifier: AWS::S3::Bucket
      Scope:
        ComplianceResourceTypes:
          - AWS::S3::Bucket

  S3PublicReadRemediation:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: !Ref S3PublicReadProhibitedRule
      TargetType: SSM_DOCUMENT
      TargetId: AWS-DisableS3BucketPublicAccess
      Automatic: true
      Parameters:
        S3BucketName:
          ResourceValue:
            Value: RESOURCE_ID
        AutomationAssumeRole:
          StaticValue:
            Values:
              - !Sub 'arn:aws:iam::${AWS::AccountId}:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole'
```

Deploy:

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name s3-security-baseline \
  --template-body file://conformance-pack.yaml \
  --region us-east-1
```

Verify both rule AND remediation landed:

```bash
aws configservice describe-remediation-configurations \
  --config-rule-names s3-bucket-public-read-prohibited
```


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **SSM Change Manager GA (2024):** Native change-approval workflow
  for SSM Automation runbooks. Required for production destructive
  remediations. Wire the remediation runbook as a Change Template
  and route through the approval workflow instead of direct
  `Automatic: true`.
- **Config conformance pack remediation enhancements:** Bulk remediation
  configurations inside the pack YAML are now first-class. Previously
  required separate `put-remediation-configurations` calls per rule.
- **Config evaluation mode (2024):** Hybrid evaluation for periodic
  rules — combines periodic with configuration-change trigger.
  Useful for IAM rules that previously could not drive resource-
  scoped remediation.
- **EventBridge global endpoints for remediation pipelines (2024-2025):**
  Multi-region failover for event-driven remediation. Useful for
  global security-baseline remediations that must continue operating
  during a regional event.
- **SSM Automation runbook versioning (2024):** Default version
  selection per document. Pin the default version explicitly to
  avoid surprise upgrades when AWS ships a new managed-runbook
  version.


## Expert heuristic: remediation blast radius (moved from SKILL.md)

Auto-remediation is the highest-leverage and highest-risk Config
feature. A single misconfigured `RemediationConfiguration` with
`Automatic: true` can revoke IAM credentials in use, detach security
groups from production instances, or terminate EC2 — across an entire
account or OU — within minutes of being enabled.

**The rule (non-negotiable):**

> ALWAYS test auto-remediation in a non-production account first, and
> scope every `RemediationConfiguration` with an explicit
> `ResourceType` filter. Never enable `Automatic: true` against an
> unbounded resource population in production on first contact.

**Why this rule exists:** AWS Config rules evaluate ALL resources of
the matched type in the rule's scope. A periodic rule with
`Scope: {ComplianceResourceTypes: ["AWS::EC2::SecurityGroup"]}` and
an automatic remediation that revokes 0.0.0.0/0 ingress will fire on
every matching SG in the account — including the one fronting your
production RDS — within one evaluation cycle. There is no dry-run
mode for `Automatic: true`.

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| `ResourceType` filter in `RemediationConfiguration` | `--remediation-configurations Parameters.ResourceType` | Restricts remediation to one resource type per config |
| Conformance pack with `Parameters` resource-id allowlist | `SSMParameter` input bound to a static list | Only listed resource IDs are remediated |
| Config rule scoped by tag | `Scope.TagKey` + `Scope.TagValue` on the rule itself | Only resources with the matching tag are evaluated NON_COMPLIANT |
| Account-level isolation | Deploy the conformance pack only to a non-production account | Zero production exposure until promotion |
| Change Manager gate | Route runbook through SSM Change Manager approval | Human approval per execution, not per config |

**Pre-production validation protocol (3-cycle rule):**

1. **Cycle 1 — MANUAL in non-prod:** Deploy the rule + remediation
   config with `Automatic: false`. Trigger
   `start-remediation-execution` manually on at least 3 sample
   NON_COMPLIANT resources. Verify all 3 succeed AND the resource
   flips to COMPLIANT in Config within 1 evaluation cycle.
2. **Cycle 2 — AUTOMATIC in non-prod:** Flip `Automatic: true`. Plant
   3 deliberately NON_COMPLIANT resources (test buckets, test SGs on
   stopped instances). Verify all 3 are remediated within
   `MaximumAutomaticAttempts × RetryAttemptSeconds` (default 30 min)
   with no false positives on adjacent resources.
3. **Cycle 3 — MANUAL in prod:** Promote the config to production
   with `Automatic: false`. Monitor for 1 week of false-positive
   NON_COMPLIANT evaluations. If zero false positives, flip to
   `Automatic: true`. If any false positive, refine the rule scope
   and re-run Cycle 2.

**Conformance pack scoping pattern (recommended for fleet rollout):**

```yaml
# Conformance pack with explicit resource scope per remediation
Resources:
  S3PublicAccessRemediation:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: s3-bucket-public-read-prohibited
      TargetType: SSM_DOCUMENT
      TargetId: AWS-DisableS3BucketPublicAccess
      Automatic: false  # Flip to true only after Cycle 2 validation
      MaximumAutomaticAttempts: 3
      RetryAttemptSeconds: 600
      Parameters:
        S3BucketName:
          ResourceValue:
            Value: RESOURCE_ID
        AutomationAssumeRole:
          StaticValue:
            Values:
              - !Sub "arn:aws:iam::${AWS::AccountId}:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"
```

**Detection of blast-radius breach post-deploy:** CloudWatch alarm on
`SSM Automation Executions Failed` > N in 5 minutes (suggests a bad
config rolling out account-wide). Also alarm on
`Config.ComplianceNonCompliantResources` increasing by > N% in one
evaluation cycle (suggests the rule scope is too broad). Both alarms
should page the on-call and trigger an EventBridge rule that flips
`Automatic` to `false` on the offending config via
`describe-remediation-configurations` + `delete-remediation-configuration` + `put-remediation-configurations` with `Automatic: false`.

**Surface in the output:** for any recommended auto-remediation,
include `BLAST_RADIUS: <scope>` (e.g., `account-wide`,
`tag-scoped:env=prod`, `conformance-pack-scoped`) and
`VALIDATION_STATUS: <pre-prod-cycle-1 | pre-prod-cycle-2 |
prod-manual | prod-automatic>`. If `VALIDATION_STATUS` is not
`prod-automatic`, do NOT mark the recommendation as deployable.
