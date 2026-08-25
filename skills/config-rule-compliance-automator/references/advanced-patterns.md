# Advanced Patterns (load on demand) — Config Rule Compliance Automator

Expert-knowledge deep dives, recipes, edge cases, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious Config behaviors (moved from SKILL.md)

- **A Config rule scoped to a resource type NOT recorded by the recorder
  will never emit NON_COMPLIANT.** Always verify the recorder's recording
  group includes the rule's target type. Dead rules = false green
  checkmark.

- **`MaximumExecutionFrequency` on periodic rules controls cadence.**
  Default is 24 hours. A non-compliant resource can exist up to 24 hours
  before detection. For security-critical rules, use `Six_Hours` or
  `One_Hour`.

- **Custom Lambda rules have a 5-minute timeout and 256MB default.**
  Multi-API rules (evaluating all S3 buckets) can timeout. Raise memory
  to 512MB+. A timeout produces "ERROR" not "NON_COMPLIANT" — the rule
  looks broken, not the resource.

- **Conformance pack `RemediationConfiguration` uses the SSM document
  NAME, not ARN.** A typo produces silent deployment failure — the pack
  reports `CREATE_COMPLETE` but remediation is not wired.

- **Organizational config rules require the `AWSServiceRoleForConfig`
  service-linked role.** Without it, `put-organization-config-rule`
  returns `AccessDenied`. Enable via `organizations enable-aws-service-
  access --service-principal config-multiaccountsetup.amazonaws.com`.

- **StackSet auto-deployment is required for ongoing compliance.** New
  accounts added to the OU after StackSet creation do NOT receive the
  conformance pack without auto-deployment enabled.

---

## Step 7 — Config Aggregator for multi-account visibility (moved from SKILL.md)

```bash
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-compliance-aggregator \
  --organization-aggregator-source \
    '{"RoleArn":"arn:aws:iam::111111111111:role/ConfigAggregatorRole","AllAwsRegions":true}'
```

Query cross-account compliance:

```bash
aws configservice describe-aggregate-compliance-by-config-rules \
  --configuration-aggregator-name org-compliance-aggregator \
  --filters '{"ConfigRuleName":"s3-bucket-server-side-encryption-enabled","ComplianceType":"NON_COMPLIANT"}'
```

**Key distinction:** the aggregator provides VISIBILITY. To REMEDIATE
across accounts, deploy remediation configurations per account via
StackSets.

---

## Step 8 — Organizational config rules (moved from SKILL.md)

```bash
# Enable Config multi-account setup
aws organizations enable-aws-service-access \
  --service-principal config-multiaccountsetup.amazonaws.com

# Deploy an org-level rule
aws configservice put-organization-config-rule \
  --organization-config-rule-name org-s3-encryption-rule \
  --organization-managed-rule-metadata \
    '{"Identifier":"S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED","ResourceTypes":["AWS::S3::Bucket"]}'

# Deploy org-level remediation
aws configservice put-organization-remediation-configuration \
  --organization-remediation-configurations '[{
    "ConfigRuleName":"org-s3-encryption-rule",
    "TargetType":"SSM_DOCUMENT","TargetId":"AWS-EnableS3BucketEncryption",
    "Automatic":true,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600
  }]'
```

Org rules deploy to ALL member accounts automatically. New accounts
receive the rule via auto-deployment.

---

## Step 9 — Custom policy rules (Git-based via CodeCommit) (moved from SKILL.md)

Custom policy rules use the Guard 2 DSL, evaluated server-side (no
Lambda cost):

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "custom-policy-no-public-s3-acl",
    "Source": {
      "Owner": "CUSTOM_POLICY",
      "SourceDetails": [{"EventSource":"aws.config","MessageType":"ConfigurationItemChangeNotification"}],
      "CustomPolicyDetails": {
        "PolicyRuntime": "guard-2",
        "PolicyText": "let s3_bucket = Resources.*[ Type == '\''AWS::S3::Bucket'\'' ]; rule s3_no_public when %s3_bucket !empty { s3_bucket.Properties.AccessControl != '\''PublicReadWrite'\'' }"
      }
    },
    "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket"]}
  }'
```

---

## Step 10 — SNS compliance notifications (moved from SKILL.md)

```python
import json, boto3
sns = boto3.client('sns')
TOPIC_ARN = 'arn:aws:sns:us-east-1:111111111111:config-compliance-alerts'

def lambda_handler(event, context):
    for record in event.get('Records', []):
        msg = json.loads(record['Sns']['Message'])
        new = msg.get('newEvaluationResult', {}).get('complianceType')
        if new == 'NON_COMPLIANT':
            rule = msg.get('configRuleName', 'unknown')
            resource = msg.get('resourceId', 'unknown')
            sns.publish(TopicArn=TOPIC_ARN,
                Message=f'NON_COMPLIANT: {rule} on {resource}',
                Subject=f'[Config Compliance] {rule}')
```

---

## Step 11 — Compliance dashboard (moved from SKILL.md)

```bash
aws cloudwatch put-dashboard \
  --dashboard-name config-compliance-dashboard \
  --dashboard-body '{
    "widgets": [{
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Config","ComplianceNonCompliantResources","ConfigRuleName","s3-bucket-server-side-encryption-enabled"],
          ["AWS/Config","ComplianceNonCompliantResources","ConfigRuleName","iam-root-access-key-check"],
          ["AWS/Config","ComplianceNonCompliantResources","ConfigRuleName","root-account-mfa-enabled"]
        ],
        "period": 300, "stat": "Maximum", "region": "us-east-1",
        "title": "Non-Compliant Resources by Rule", "view": "timeSeries"
      }
    }]
  }'
```

---

## Step 12 — Drift detection (moved from SKILL.md)

**CloudFormation drift (IaC divergence):**

```bash
aws cloudformation detect-stack-drift --stack-name my-compliant-stack
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <id>
```

**Config drift (configuration timeline):**

```bash
aws configservice get-resource-config-history \
  --resource-type AWS::S3::Bucket --resource-id my-bucket --limit 10
```

Alert on drift via EventBridge:

```bash
aws events put-rule --name config-drift-detection \
  --event-pattern '{"source":["aws.config"],"detail-type":["Config Configuration Item Change"],"detail":{"configurationItemDiff":{"changeType":["UPDATE"]}}}'
```

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Organizational config rules GA (2024):** Org-level rule deployment
  with auto-propagation to member accounts.
- **Custom policy rules with Guard 2 (2024-2025):** Server-side policy
  evaluation, eliminating Lambda runtime costs for policy-expressible
  rules.
- **Config drift detection enhancements (2025):** Real-time drift alerts
  via EventBridge with diff metadata in the event payload.
- **Config Aggregator cost optimization (2025):** Selective aggregation
  — aggregate only specific rules per account, reducing costs.
- **StackSet auto-deployment with OU targeting (2024):** New accounts
  added to a targeted OU automatically receive the StackSet.
- **Config conformance pack template builder (2024-2025):** Visual
  template builder for composing conformance packs from managed rule
  libraries.

---

## Expert heuristic: managed vs custom rule selection + SSM remediation document lifecycle + conformance pack deployment via StackSets (moved from SKILL.md)

The highest-leverage Config compliance pattern is a three-layer
deployment: prefer managed rules wherever possible, wire SSM remediation
with appropriate trigger semantics, and deploy the baseline via
StackSets with auto-deployment enabled.

**The rule (non-negotiable):**

> ALWAYS prefer managed rules when they exist (80+ available, AWS-
> maintained, no Lambda cost). For gaps, use custom policy rules (Guard
> 2, server-side) before falling back to custom Lambda rules. Deploy
> the entire compliance baseline via StackSets with auto-deployment
> enabled, targeting the full OU and all active regions. Never deploy a
> compliance baseline to a single account or single region.

**SSM remediation document lifecycle:**

| Phase | Action |
|---|---|
| Select | Check for managed runbook (`AWS-*` prefix) |
| Build (if custom) | Create document, test in pre-prod |
| Wire | `put-remediation-configurations` with trigger semantics |
| Backlog | `start-remediation-execution` for existing NON_COMPLIANT |
| Verify | `describe-remediation-execution-status` + Config timeline |

**Conformance pack deployment checklist:**

| Item | Required |
|---|---|
| `CAPABILITY_IAM CAPABILITY_NAMED_IAM` on StackSet | YES |
| `SERVICE_MANAGED` permission model | YES |
| Auto-deployment enabled | YES |
| All active regions in `--regions` | YES |
| RemediationConfiguration resources in pack YAML | YES (not implicit) |
| SNS topic for compliance notifications | Recommended |
| Config recorder active in each target account | YES |

**Surface in output:** include `MANAGED_RULE_COUNT: <n>`,
`CUSTOM_RULE_COUNT: <n>`, `AUTO_DEPLOYMENT: enabled|disabled`, and
`REGION_COVERAGE: <n>`. If `REGION_COVERAGE` is 1 or `AUTO_DEPLOYMENT`
is disabled, do NOT mark as deployable.
