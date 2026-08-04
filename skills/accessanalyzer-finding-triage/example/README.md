# End-to-End Example: Access Analyzer Finding Triage

A walkthrough showing how to use the `accessanalyzer-finding-triage` skill
from invocation through remediation. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

Your security team has configured IAM Access Analyzer and is reviewing the
active findings. You need to triage 4 findings — 2 external-access findings
and 2 unused-access findings — and produce a prioritized remediation plan.

The findings are:

1. **`kms-external-public`** — KMS key with `Principal: "*"`, no condition,
   `isPublic: true`, actions include `kms:Decrypt`.
2. **`s3-cloudtrail-source-arn`** — S3 bucket with external account principal
   but `aws:SourceArn` condition bounding the access.
3. **`unused-role-legacy-etl`** — IAM role unused for 95 days with production
   S3 access.
4. **`iam-role-trust-lambda`** — Role trust policy with
   `lambda.amazonaws.com` service principal.

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:triage-accessanalyzer-findings
```

Then paste the four finding configurations.

### Option B: Natural language

```
You: "Triage these Access Analyzer findings:

  Finding: kms-external-public
  Type: ExternalAccess
  Resource: AWS::KMS::Key
  Principal: '*'
  isPublic: true
  Actions: kms:Decrypt, kms:Encrypt
  Condition: {}
  Status: ACTIVE

  Finding: s3-cloudtrail-source-arn
  Type: ExternalAccess
  Resource: AWS::S3::Bucket
  Principal: arn:aws:iam::999999999999:root
  isPublic: false
  Actions: s3:GetBucketAcl, s3:PutObject
  Condition: aws:SourceArn=arn:aws:cloudtrail:us-east-1:999999999999:trail/org-trail
  Status: ACTIVE

  Finding: unused-role-legacy-etl
  Type: UnusedIAMRole
  Resource: arn:aws:iam::123456789012:role/legacy-etl-role
  Last accessed: 95 days ago
  Status: ACTIVE

  Finding: iam-role-trust-lambda
  Type: ExternalAccess
  Resource: AWS::IAM::Role
  Principal: {'Service': 'lambda.amazonaws.com'}
  isPublic: false
  Actions: sts:AssumeRole
  Condition: {}
  Status: ACTIVE
"
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "triage my access analyzer findings"
```

Output:

```
[Phase: Audit | Skills routed: accessanalyzer-finding-triage]

Primary route: accessanalyzer-finding-triage (score: 18)
```

---

## Step 2 — Skill produces deterministic verdicts

The skill applies its classification logic in order (condition strength,
principal type, resource-type severity) and emits a per-finding report:

```text
FINDING: kms-external-public
RESOURCE: arn:aws:kms:us-east-1:123456789012:key/abc123def456
RESOURCE_TYPE: AWS::KMS::Key
FINDING_TYPE: ExternalAccess
VERDICT: EXTERNAL_ACCESS
RISK: CRITICAL
REASON: Principal "*" with no restrictive condition grants kms:Decrypt on a
        KMS key. isPublic is true. KMS decrypt access is CRITICAL because it
        provides full data access to anything encrypted with this key —
        anyone on the internet can decrypt ciphertext encrypted with this key.
REMEDIATION: IMMEDIATE — restrict the KMS key policy to named internal
             principals only. Capture current policy first:
             aws kms get-key-policy --key-id abc123def456 --policy-name
             default > /tmp/kms-backup.json
             Then remove the Principal "*" statement and replace with specific
             IAM role ARNs. Audit CloudTrail for kms:Decrypt events from
             unknown principals during the exposure window.

FINDING: s3-cloudtrail-source-arn
RESOURCE: arn:aws:s3:::org-cloudtrail-logs
RESOURCE_TYPE: AWS::S3::Bucket
FINDING_TYPE: ExternalAccess
VERDICT: SAFE
RISK: LOW
REASON: Finding is valid (external account 999999999999 has access) but the
        aws:SourceArn condition cryptographically bounds the access to the
        specific CloudTrail trail. The external principal cannot exploit this
        access without the source trail existing and making the request.
REMEDIATION: No remediation required. Optionally create an archive rule to
             suppress future instances: filter on resourceType
             AWS::S3::Bucket + condition aws:SourceArn.

FINDING: unused-role-legacy-etl
RESOURCE: arn:aws:iam::123456789012:role/legacy-etl-role
RESOURCE_TYPE: AWS::IAM::Role
FINDING_TYPE: UnusedIAMRole
VERDICT: UNUSED_ACCESS
RISK: MODERATE
REASON: Role unused for 95 days (last accessed 2024-10-15). Stale identity
        expands the attack surface — the role has s3:GetObject and
        s3:PutObject on production data buckets. If session tokens were
        cached before the role became inactive, they could still be valid.
REMEDIATION: Validate no workload depends on this role (check CloudTrail for
             AssumeRole events in the last 30 days). If confirmed unused:
             detach policies and delete the role. Capture config first:
             aws iam get-role --role-name legacy-etl-role >
             /tmp/legacy-etl-role-backup.json

FINDING: iam-role-trust-lambda
RESOURCE: arn:aws:iam::123456789012:role/lambda-report-generator
RESOURCE_TYPE: AWS::IAM::Role
FINDING_TYPE: ExternalAccess
VERDICT: EXPECTED
RISK: LOW
REASON: Principal is the AWS service principal lambda.amazonaws.com granting
        sts:AssumeRole. This is the standard pattern for a Lambda execution
        role trust policy — Lambda must assume the role to execute the
        function. Matches the expected service integrations table.
REMEDIATION: Create an archive rule to suppress future instances:
             filter on resourceType AWS::IAM::Role + principal
             lambda.amazonaws.com + action sts:AssumeRole. Document the
             Lambda function that uses this role and the owner.
```

---

## Step 3 — Pipeline integration (Prioritize + Remediate)

When invoked through the orchestrator (`/aws:pipeline`), the findings flow
into the Prioritize and Remediate phases:

```
[Phase: Prioritize | Findings: 1 CRITICAL, 1 MODERATE, 2 LOW | Skills routed: orchestrator]

1. CRITICAL: kms-external-public — KMS key public decrypt (data breach risk) — fix NOW
2. MODERATE: unused-role-legacy-etl — stale role with prod S3 access — fix this week
3. LOW: s3-cloudtrail-source-arn — condition-bounded, no action needed
4. LOW: iam-role-trust-lambda — expected Lambda integration, archive

[Phase: Remediate | Skills routed: accessanalyzer-finding-triage]

Immediate containment (kms-external-public — incident response):

  # Capture current policy before modifying
  aws kms get-key-policy \
    --key-id abc123def456 \
    --policy-name default \
    > /tmp/kms-abc123-backup-$(date +%s).json

  # Restrict to internal principals (replace the wildcard statement)
  aws kms put-key-policy \
    --key-id abc123def456 \
    --policy-name default \
    --policy file://scoped-kms-policy.json

  # Audit exposure window
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=Decrypt \
    --start-time 2024-06-15T00:00:00Z \
    --end-time 2025-01-20T23:59:59Z

Stale role cleanup (unused-role-legacy-etl):

  # Check for any recent AssumeRole events
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
    --start-time 2025-01-01T00:00:00Z \
    --end-time 2025-01-20T23:59:59Z \
    | grep legacy-etl-role

  # If unused, detach policies and delete
  aws iam delete-role --role-name legacy-etl-role

Archive rule (iam-role-trust-lambda — expected integration):

  aws accessanalyzer create-archive-rule \
    --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/ConsoleAnalyzer \
    --rule-name suppress-lambda-assume-role \
    --filter '{"resourceType":{"eq":["AWS::IAM::Role"]},"principal":{"contains":["lambda.amazonaws.com"]},"action":{"contains":["sts:AssumeRole"]}}'
```

---

## Step 4 — Post-remediation verification

Re-run the finding list after remediation. Expected output:

```text
FINDING: kms-external-public
VERDICT: SAFE
REASON: Finding status is RESOLVED — Access Analyzer re-evaluated the KMS key
        and the public-access path no longer exists.
REMEDIATION: None required. Verify no application breakage from the policy
             change.

FINDING: s3-cloudtrail-source-arn
VERDICT: SAFE
REASON: Condition aws:SourceArn bounds access — unchanged.

FINDING: unused-role-legacy-etl
VERDICT: SAFE
REASON: Role has been deleted — finding will auto-resolve on next analysis.

FINDING: iam-role-trust-lambda
VERDICT: EXPECTED
REASON: Archived via suppress-lambda-assume-role rule — no longer appears in
        active findings.
```

---

## What the skill catches that a naive review misses

| Finding | Naive review | Skill verdict | Why the skill is right |
|---|---|---|---|
| `kms-external-public` | "KMS key is public, restrict it" | EXTERNAL_ACCESS / CRITICAL | The skill identifies KMS decrypt as CRITICAL (data-access multiplier) and prescribes incident-response priority with CloudTrail audit, not just "restrict the policy." |
| `s3-cloudtrail-source-arn` | "External account has access, investigate" | SAFE | The skill recognizes `aws:SourceArn` as a cryptographic condition — the external account cannot exploit the access without the named CloudTrail trail. A naive review wastes time investigating a non-risk. |
| `unused-role-legacy-etl` | "Delete the unused role" | UNUSED_ACCESS / MODERATE | The skill prescribes a validation step (check CloudTrail for AssumeRole events) before deletion, and notes that session tokens may still be valid — a naive review would delete without validation. |
| `iam-role-trust-lambda` | "External principal, restrict the trust policy" | EXPECTED | The skill recognizes `lambda.amazonaws.com` in a role trust policy as the standard Lambda execution role pattern. A naive review creates a false-positive ticket for a normal AWS integration. |

---

## Related artifacts

- **Skill definition:** `skills/accessanalyzer-finding-triage/SKILL.md`
- **Slash command:** `commands/aws/triage-accessanalyzer-findings.md`
- **Eval suite:** `skills/accessanalyzer-finding-triage/evals/evals.json`
- **Legacy test cases:** `skills/accessanalyzer-finding-triage/eval/test-cases.yaml`
