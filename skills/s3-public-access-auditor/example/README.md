# End-to-End Example: S3 Public-Access Audit

A walkthrough showing how to use the `s3-public-access-auditor` skill from
invocation through remediation. Mirrors the structured-eval pattern of shipping a
concrete worked example per skill.

---

## Scenario

You are onboarding a new AWS account and need to audit 3 S3 buckets for
public access exposure before granting production access. The buckets are:

1. **`app-uploads-prod`** — user-uploaded content; BPA off, bucket policy
   grants `s3:GetObject` to `Principal: "*"`.
2. **`logs-archive-2024`** — CloudTrail log archive; BPA off, ACL grants
   READ to `AllUsers`.
3. **`backup-exports`** — database export bucket; BPA fully enabled, no
   policy.

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:audit-s3-public-access
```

Then paste the three bucket configurations.

### Option B: Natural language

```
You: "Audit these 3 S3 buckets for public access exposure:

  Bucket: app-uploads-prod
  BPA: all False
  ACL: private
  Policy: Allow s3:GetObject to Principal "*" on
          arn:aws:s3:::app-uploads-prod/*

  Bucket: logs-archive-2024
  BPA: all False
  ACL: READ to AllUsers
  Policy: (none)

  Bucket: backup-exports
  BPA: all True
  ACL: private
  Policy: (none)
"
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "audit my S3 buckets for public access"
```

Output:

```
[Phase: Audit | Skills routed: s3-public-access-auditor]

Primary route: s3-public-access-auditor (score: 18)
```

---

## Step 2 — Skill produces deterministic verdicts

The skill applies its classification logic in AWS precedence order
(BPA -> policy -> ACL -> condition) and emits a per-bucket report:

```text
BUCKET: app-uploads-prod
VERDICT: PUBLIC
REASON: Rule 2 (unrestricted wildcard Allow) — BPA is not fully enabled and
        the bucket policy has an Allow with Principal "*", Action
        s3:GetObject, and no restrictive Condition. HIGH severity (read-only
        data exfiltration — anyone on the internet can download user
        uploads).
REMEDIATION: Enable BPA at both account and bucket level (all 4 settings
             True). Remove or restrict the public-read policy statement. If
             public CDN access is intended, use CloudFront with Origin
             Access Control (OAC) instead of a bucket-level public policy.

BUCKET: logs-archive-2024
VERDICT: PUBLIC
REASON: Rule 3 (legacy ACL grant) — BPA is not fully enabled and the ACL
        grants READ to AllUsers
        (http://acs.amazonaws.com/groups/global/AllUsers). HIGH severity
        (public read of CloudTrail log archive — potential compliance data
        exposure).
REMEDIATION: Enable BPA at both account and bucket level (all 4 settings
             True). Remove the AllUsers ACL grant:
             aws s3api put-bucket-acl --bucket logs-archive-2024 --acl private

BUCKET: backup-exports
VERDICT: SAFE
REASON: Rule 1 (BPA authoritative) — all 4 BPA settings are True at the
        bucket level. Bucket-level BPA is authoritative regardless of
        account-level BPA state. No public ACLs or policies present.
REMEDIATION: None required. BPA is authoritative. Optionally enable
             account-level BPA as defense-in-depth for future buckets.
```

---

## Step 3 — Pipeline integration (Prioritize + Remediate)

When invoked through the orchestrator (`/aws:pipeline`), the findings flow
into the Prioritize and Remediate phases:

```
[Phase: Prioritize | Findings: 2 HIGH | Skills routed: orchestrator]

1. HIGH: app-uploads-prod — PUBLIC via unrestricted wildcard policy
   (user uploads exposed to the internet)
2. HIGH: logs-archive-2024 — PUBLIC via AllUsers ACL
   (CloudTrail logs exposed to the internet)
3. —: backup-exports — SAFE (no action)

[Phase: Remediate | Skills routed: s3-public-access-auditor]

Bucket-level BPA (fastest containment — apply to both PUBLIC buckets):

  aws s3api put-public-access-block \
    --bucket app-uploads-prod \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  aws s3api put-public-access-block \
    --bucket logs-archive-2024 \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

ACL cleanup (logs-archive-2024):

  aws s3api put-bucket-acl --bucket logs-archive-2024 --acl private

Policy removal (app-uploads-prod — capture backup first):

  aws s3api get-bucket-policy --bucket app-uploads-prod --output json > /tmp/app-uploads-prod-policy-backup.json
  aws s3api delete-bucket-policy --bucket app-uploads-prod

Account-level BPA (defense-in-depth for all current + future buckets):

  aws s3control put-public-access-block \
    --account-id <account-id> \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Step 4 — Post-remediation verification

Re-run the audit on the same buckets after remediation. Expected output:

```text
BUCKET: app-uploads-prod
VERDICT: SAFE
REASON: Rule 1 (BPA authoritative) — all 4 BPA settings True at bucket level.
REMEDIATION: None required.

BUCKET: logs-archive-2024
VERDICT: SAFE
REASON: Rule 1 (BPA authoritative) — all 4 BPA settings True at bucket level.
REMEDIATION: None required.

BUCKET: backup-exports
VERDICT: SAFE
REASON: Rule 1 (BPA authoritative) — unchanged.
REMEDIATION: None required.
```

All three buckets now classify as SAFE via Rule 1 (BPA authoritative).

---

## What the skill catches that a naive review misses

| Bucket | Naive review | Skill verdict | Why the skill is right |
|---|---|---|---|
| `app-uploads-prod` | "private ACL, looks OK" | PUBLIC (Rule 2) | The ACL is private but the bucket policy grants public read — AWS unions ACL + policy; the policy overrides the private ACL. |
| `logs-archive-2024` | "no bucket policy, probably safe" | PUBLIC (Rule 3) | The AllUsers ACL grant is a legacy public-access vector that does not require a bucket policy. `AllUsers` means anyone on the internet, not just account users. |
| `backup-exports` | "safe" | SAFE (Rule 1) | Correct verdict, but the skill cites BPA-authoritative reasoning and recommends account-level BPA as defense-in-depth — the naive review would not. |

---

## Related artifacts

- **Skill definition:** `skills/s3-public-access-auditor/SKILL.md`
- **BPA CLI reference:** `skills/s3-public-access-auditor/references/bpa-settings-and-cli-commands.md`
- **Slash command:** `commands/aws/audit-s3-public-access.md`
- **Eval suite:** `skills/s3-public-access-auditor/evals/evals.json`
- **Legacy test cases:** `skills/s3-public-access-auditor/eval/test-cases.yaml`
