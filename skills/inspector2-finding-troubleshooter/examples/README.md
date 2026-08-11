# End-to-End Example: Inspector v2 Finding Troubleshooting

A walkthrough showing how to use the `inspector2-finding-troubleshooter`
skill from invocation through remediation. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are triaging a CRITICAL PACKAGE_VULNERABILITY finding on an EC2
instance. The finding reports:

- Finding ARN: `arn:aws:inspector2:us-east-1:111:finding/abc123`
- Type: PACKAGE_VULNERABILITY
- CVE: CVE-2024-5555
- Package: openssl
- Installed version: 3.0.7-1.amzn2023.1
- Vulnerable range: < 3.0.8
- Fixed-in version: 3.0.8-1.amzn2023.1
- Severity: CRITICAL
- Resource: `arn:aws:ec2:us-east-1:111:instance/i-0abc123def456`
- lastObservedAt: 2026-08-09T18:00Z

Instance: Amazon Linux 2023, SSM-managed, online.

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:troubleshoot-inspector2-finding
```

Then paste the finding context.

### Option B: Natural language

```
You: "Inspector v2 fired a CRITICAL finding on EC2 instance
      i-0abc123def456. CVE-2024-5555 on openssl at 3.0.7.
      Fixed-in 3.0.8. SSM-managed. Account 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "diagnose inspector v2 finding"
```

Output:

```
[Phase: Troubleshoot | Skills routed: inspector2-finding-troubleshooter]

Primary route: inspector2-finding-troubleshooter (score: 22)
```

---

## Step 2 — Skill produces the diagnostic block

```text
TARGET: arn:aws:ec2:us-east-1:111:instance/i-0abc123def456
VERDICT: ROOT_CAUSE_FOUND
REASON: Instance has openssl at 3.0.7-1.amzn2023.1 which is within
  CVE-2024-5555 vulnerable range; fixed version 3.0.8-1.amzn2023.1
  is available in the SSM Patch Baseline.
FINDING_TYPE: PACKAGE_VULNERABILITY
SEVERITY: CRITICAL
LAYER: EC2_OS_PACKAGE
EVIDENCE:
  - Finding: PACKAGE_VULNERABILITY, CVE-2024-5555, CRITICAL,
    lastObservedAt 2026-08-09T18:00Z.
  - Probe: aws ssm list-inventory-entries --instance-id i-0abc123
    --type AWS:Application --filters Key=Name,Values=openssl
    returns Version: 3.0.7-1.amzn2023.1.
  - Probe: aws ssm describe-patches --filters Key=PRODUCT,
    Values=AmazonLinux2023 returns Version: 3.0.8-1.amzn2023.1
    for CVE-2024-5555.
  - Passing: instance is SSM-managed; SSM agent online.
REMEDIATION:
  1. Apply the missing update via SSM Run Command:
     aws ssm send-command --instance-ids i-0abc123
       --document-name AWS-RunPatchBaseline
  2. Wait for the next Inspector scan; finding auto-closes.
  3. Verify: list-inventory-entries shows openssl 3.0.8.
CONFIRM: Before running AWS-RunPatchBaseline, emit and await:
  "CONFIRM: About to apply patches on i-0abc123 (openssl 3.0.7
   -> 3.0.8). Proceed? (yes/no)"
```

---

## Step 3 — Verification after remediation

```bash
# Confirm the patched version via SSM inventory
aws ssm list-inventory-entries --instance-id i-0abc123def456 \
  --type "AWS:Application" \
  --filters "Key=Name,Values=openssl" --output json

# Confirm the finding closes on the next Inspector scan
aws inspector2 list-findings \
  --filter-criteria "FindingArn=[{Comparison=EQUALS,Value=arn:aws:inspector2:us-east-1:111:finding/abc123}]" \
  --query 'findings[0].{State:State,LastObservedAt:lastObservedAt}' \
  --output json
```

---

## What the skill catches that a naive triage misses

| Triage step | Naive response | Skill output | Why the skill is right |
|---|---|---|---|
| Finding classification | "It's a CVE, patch it" | FINDING_TYPE: PACKAGE_VULNERABILITY, LAYER: EC2_OS_PACKAGE | The finding type drives the diagnostic; package CVEs route to SSM inventory, not SG checks. |
| Version verification | Assumes the CVE is current | Probes SSM inventory; confirms 3.0.7 < 3.0.8 | A finding may be stale; verifying the installed version prevents unnecessary patch operations. |
| Patch availability | Runs `send-command` blindly | Checks `describe-patches` for the fixed-in version | If the patch is not in the baseline, the run command does nothing. |
| Stale-finding handling | Re-patches already-patched packages | Recognizes STALE_FINDING layer; recommends rescan | Avoids redundant work; the finding auto-closes on rescan. |
| Reachability vs package | Confuses the two finding types | Routes SG findings to SG remediation, package findings to SSM | Wrong fix surface = wasted remediation window. |
| Lambda code vuln | Recommends runtime update | Routes to source code fix + key rotation | Code findings are source defects; runtime updates do not close them. |
| Confirmation gate | Executes state-changing CLIs | Emits CONFIRM prompt and awaits approval | Operator must approve any patch / SG / Lambda update before execution. |

---

## Related artifacts

- **Skill definition:** `skills/inspector2-finding-troubleshooter/SKILL.md`
- **Finding types reference:** `skills/inspector2-finding-troubleshooter/references/finding-types-reference.md`
- **Slash command:** `commands/aws/troubleshoot-inspector2-finding.md`
- **Eval suite:** `skills/inspector2-finding-troubleshooter/evals/evals.json`
- **Legacy test cases:** `skills/inspector2-finding-troubleshooter/eval/test-cases.yaml`
