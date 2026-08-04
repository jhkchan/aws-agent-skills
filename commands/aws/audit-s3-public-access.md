---
description: Audit S3 bucket configurations for public access exposure (BPA, ACLs, bucket policies). Emits a deterministic VERDICT per bucket.
nl_triggers:
  - "is this s3 bucket public"
  - "check my buckets for public access"
  - "audit s3 public access"
  - "s3 exposure check"
  - "bpa settings"
  - "block public access"
  - "bucket policy audit"
  - "s3 acl check"
  - "allusers acl"
  - "authenticatedusers"
  - "s3 data leak"
  - "principal star s3"
  - "s3:getobject public"
routes_to: s3-public-access-auditor
---

# /aws:audit-s3-public-access

Activate the `s3-public-access-auditor` skill and audit S3 bucket
configurations for public access exposure.

## What it does

The skill analyzes three independent S3 access-control planes in AWS
precedence order and emits a deterministic verdict per bucket:

```
BPA (hard gate) -> Bucket Policy -> ACL -> Condition strength
```

For each bucket, the skill outputs:

```text
BUCKET: <name>
VERDICT: PUBLIC | SAFE | AMBIGUOUS
REASON: <cites the specific rule number and severity>
REMEDIATION: <specific action or "None required">
```

## When to use

- You have S3 bucket config text (BPA settings, ACL, bucket policy JSON) and
  need to know if it is publicly accessible.
- You are reviewing S3 security before a production deployment.
- You need specific remediation commands (not just "it's bad").
- You are triaging a potential data-leak incident.

## How to invoke

### Slash command

```
/aws:audit-s3-public-access
```

Then paste the bucket configuration (BPA settings, ACL, bucket policy JSON).

### Natural language

Any of these routes to the same skill:

- "is this S3 bucket public?"
- "check my buckets for public access"
- "audit this bucket policy for exposure"
- "BPA settings check"
- "does this bucket have an AllUsers ACL?"

### CLI routing

```bash
node cli/bin/cli.js route "check my S3 buckets for public access"
```

The CLI scores the prompt against all skill keywords + descriptions and emits
a phase indicator:

```
[Phase: Audit | Skills routed: s3-public-access-auditor]
```

## Pipeline integration

This skill operates in **Phase 2 (Audit)** of the CloudOps pipeline. The
orchestrator routes to it when the assessment enters the Audit phase and S3
buckets are in scope. Findings flow into Phase 3 (Prioritize) for severity
ranking and Phase 4 (Remediate) for CLI command generation.

**Severity mapping:**

| Verdict | Severity | Why |
|---|---|---|
| PUBLIC (write-capable) | CRITICAL | Write-open bucket = ransomware / data-destruction surface |
| PUBLIC (read-only) | HIGH | Data exfiltration via `s3:GetObject` / `s3:List*` |
| AMBIGUOUS | MEDIUM | Condition-restricted; fragile but not directly public |
| SAFE | — | No action required (BPA recommended as defense-in-depth) |

## Example

```
You: /aws:audit-s3-public-access

     Bucket: my-app-uploads
     BPA: all 4 settings False
     ACL: private
     Policy: {Effect: Allow, Principal: "*", Action: "s3:GetObject",
              Resource: "arn:aws:s3:::my-app-uploads/*"}

Skill:
  BUCKET: my-app-uploads
  VERDICT: PUBLIC
  REASON: Rule 2 (unrestricted wildcard Allow) — Principal "*" with
          s3:GetObject and no restrictive condition; HIGH severity
          (read-only data exfiltration).
  REMEDIATION: Enable BPA (all 4 settings at account + bucket level).
               Remove or restrict the public policy statement. If public
               CDN access is intended, use CloudFront OAC instead of a
               bucket-level public policy.
```

## References

- Skill definition: `skills/s3-public-access-auditor/SKILL.md`
- BPA CLI commands: `skills/s3-public-access-auditor/references/bpa-settings-and-cli-commands.md`
- End-to-end example: `skills/s3-public-access-auditor/example/README.md`
- Eval suite: `skills/s3-public-access-auditor/evals/evals.json`
