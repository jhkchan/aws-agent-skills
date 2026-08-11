# End-to-End Example: Macie Data Discovery Operation

A walkthrough showing how to use the `macie-data-discovery-operator`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are creating a daily scheduled Macie classification job on your
production data buckets. The setup needs:

- Macie already enabled (FIFTEEN_MINUTES finding publish frequency)
- Daily scheduled classification job on prod-data-bucket + financial-records
- RECOMMENDED managed data identifier selector
- Custom data identifier for internal employee ID format (EMP######)
- EventBridge rule for high-severity finding remediation

Job name: `daily-pii-scan`
Account: `123456789012`
Region: `us-east-1`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:operate-macie-data-discovery
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Macie classification job named daily-pii-scan for
      production buckets prod-data-bucket and financial-records in
      account 123456789012. Daily schedule. RECOMMENDED identifiers.
      Also create a custom data identifier for employee IDs (EMP######)
      with keywords. Macie is enabled."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create macie classification job"
```

---

## Step 2 — Skill produces the VERDICT block

```text
OPERATION: classify
VERDICT: READY
TARGET: daily-pii-scan
PRE_CHECKS:
  - [PASS] Macie session ENABLED (get-macie-session status=ENABLED)
  - [PASS] Target bucket prod-data-bucket exists in account 123456789012
  - [PASS] Target bucket financial-records exists in account 123456789012
  - [PASS] IAM role has macie2:CreateClassificationJob permission
STEPS:
  1. CONFIRM: About to create scheduled classification job daily-pii-scan on buckets prod-data-bucket and financial-records in account 123456789012 region us-east-1. This will scan daily using RECOMMENDED managed identifiers. Proceed? (yes/no)
  2. aws macie2 create-classification-job --name daily-pii-scan --job-type SCHEDULED --schedule-frequency '{dailySchedule:{}}' --s3-job-definition bucketDefinitions='[{accountId=123456789012,buckets=[prod-data-bucket,financial-records]}]' --managed-data-identifier-selector RECOMMENDED --description "Daily PII scan of production data buckets"
POST_VERIFY:
  - (pending execution)
  - describe-classification-job returns jobStatus RUNNING then COMPLETE
STATE: pending — will be RUNNING after creation, COMPLETE after first scan
NOTES: RECOMMENDED selector lets Macie sample bucket content and select relevant identifiers. Job runs daily. Findings published at FIFTEEN_MINUTES frequency.
```

---

## Step 3 — Create the custom data identifier

```bash
aws macie2 create-custom-data-identifier \
  --name "employee-id-pattern" \
  --regex "EMP[0-9]{6}" \
  --keywords employee emp_id staff id \
  --ignore-words example test sample demo \
  --maximum-match-distance 50 \
  --severity-levels HIGH \
  --description "Detects EMP###### employee ID format"
```

---

## Step 4 — Set up remediation (EventBridge + Lambda)

```bash
# EventBridge rule for high-severity findings
aws events put-rule \
  --name "macie-finding-trigger" \
  --event-pattern '{
    "source": ["aws.macie"],
    "detail-type": ["Macie Finding"],
    "detail": {
      "severity": ["High", "Critical"]
    }
  }'

aws events put-targets \
  --rule "macie-finding-trigger" \
  --targets '[{"Id":"macie-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:123456789012:function:macie-remediate"}]'
```

---

## Step 5 — Post-deployment verification

```bash
# Verify classification job
aws macie2 describe-classification-job --job-id <job-id>

# Verify custom data identifier
aws macie2 get-custom-data-identifier --id <custom-id>

# List recent findings
aws macie2 list-findings \
  --finding-criteria \
    criterion='{createdAt:{gte:"2026-08-09T00:00:00Z"}}' \
  --sort createdAt:desc

# Verify EventBridge rule
aws events describe-rule --name macie-finding-trigger
```

---

## What the skill catches that a naive operation misses

| Configuration | Naive operation | Skill output | Why the skill is right |
|---|---|---|---|
| Macie enablement | Jumps to create-classification-job | Checks get-macie-session first | Jobs fail silently without Macie enabled |
| Identifier selector | Uses ALL (all 150+ identifiers) | RECOMMENDED (content-adaptive) | ALL scans region-irrelevant identifiers; RECOMMENDED adapts |
| Custom identifier keywords | Omits --keywords | Includes proximity keywords | Without keywords, every regex match is reported — massive false positives |
| Custom identifier ignore words | Omits --ignore-words | Includes test data exclusions | Without ignore words, test/sample data generates findings |
| Remediation scope | Triggers on ALL findings | Scoped to High/Critical severity | Blanket remediation breaks production; severity scoping targets real risks |
| Suppression documentation | Suppresses silently | Documents rationale in description | Undocumented suppression masks real risks |
| Security Hub enablement | Forgets to enable SH | Enables SH before Macie integration | Macie integration fails if SH not enabled |

---

## Related artifacts

- **Skill definition:** `skills/macie-data-discovery-operator/SKILL.md`
- **Detection and remediation guide:** `skills/macie-data-discovery-operator/references/detection-and-remediation.md`
- **Operating CLI commands:** `skills/macie-data-discovery-operator/references/operating-cli-commands.md`
- **Slash command:** `commands/aws/operate-macie-data-discovery.md`
- **Eval suite:** `skills/macie-data-discovery-operator/evals/evals.json`
- **Legacy test cases:** `skills/macie-data-discovery-operator/eval/test-cases.yaml`
