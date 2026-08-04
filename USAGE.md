# USAGE — AWS CloudOps Agent Skills

Detailed per-skill invocation guide plus a full end-to-end CloudOps-audit
pipeline walkthrough. For install instructions, see the
[README](README.md). For slash-command reference, see the table below.

---

## Slash Command Quick Reference

| Command | Phase | What it does |
|---|---|---|
| `/aws:pipeline` | All | Start or resume the full CloudOps pipeline from the orchestrator |
| `/aws:status` | — | Emit `[Phase: X | Resources: Y | Skills routed: Z]` one-liner |
| `/aws:help` | — | List all commands + natural-language triggers + skill inventory |
| `/aws:audit-s3-public-access` | 2 Audit | Audit S3 bucket configs for public exposure — emits VERDICT per bucket |
| `/aws:audit-iam-least-privilege` | 2 Audit | Classify an IAM policy document for wildcard/escalation risk (routes to `iam-least-privilege-advisor`) |
| `/aws:audit-ec2-security-groups` | 2 Audit | Audit EC2 security groups for exposed ports and compliance violations |

Every command has a natural-language equivalent — the orchestrator routes
identically.

## CLI Quick Reference

```bash
# List all discovered skills
node cli/bin/cli.js list

# Route a prompt to the best-matching skill(s)
node cli/bin/cli.js route "check my S3 buckets for public access"

# Validate all skills against the schema
node cli/bin/cli.js validate

# Show skill-suite coverage + eval status
node cli/bin/cli.js status
```

---

## The CloudOps Pipeline (4 phases)

```
Assess         →     Audit          →     Prioritize       →     Remediate
   |                  |                     |                      |
   v                  v                     v                      v
inventory          detective              severity ranking         CLI commands
resource lists     auditors               cost-impact              IaC patches
coverage gaps      deterministic          compliance-mandate       runbook steps
baseline state     VERDICT output         risk-weighted            actionable fixes
```

The orchestrator diagnoses which phase the assessment is in and routes to the
right specialist skill(s). It never duplicates specialist content — always
hands off.

---

## Per-Skill Usage

### 1. aws-orchestrator (entry point)

**Pipeline phase:** Phase 0 — routes all phases.

**What it does:** Diagnoses where the assessment sits in the CloudOps pipeline
(Assess -> Audit -> Prioritize -> Remediate) and routes to the right
specialist skill(s). Emits a phase indicator like
`[Phase: Audit | Skills routed: s3-public-access-auditor]`. Never duplicates
specialist content — always hands off.

**When to invoke (trigger phrases):**

- "check my AWS security posture"
- "audit my whole account"
- "what should I audit first?"
- "help me prioritize these findings"
- "full compliance audit"
- A bare AWS resource name + any audit verb ("audit this bucket", "check this role")

**Example prompt:**

```
You: "I'm onboarding a new AWS account. Audit everything for public
     exposure and give me a prioritized remediation plan."
```

**Expected behavior:**

1. Orchestrator emits phase plan covering all 4 phases.
2. Routes Phase 1 (Assess) -> all skills in discovery mode (inventory).
3. Routes Phase 2 (Audit) -> each specialist for VERDICT.
4. Routes Phase 3 (Prioritize) -> orchestrator ranks findings cross-service.
5. Routes Phase 4 (Remediate) -> each specialist's remediation section.
6. Emits `[Phase: X | Skills routed: Y]` at each transition.

---

### 2. s3-public-access-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-s3-public-access`

**What it does:** Analyzes S3 bucket configurations (Block Public Access
settings, ACLs, and bucket policies) to determine which buckets are publicly
accessible, classify each bucket's exposure level, and provide specific
remediation guidance.

**When to invoke (trigger phrases):**

- "is this S3 bucket public?"
- "check my buckets for public access"
- "BPA settings", "Block Public Access"
- "bucket policy", "ACL", "AllUsers"
- "s3 exposure", "data leak"
- reviewing S3 security before production deployment

**Example prompt:**

```
You: /aws:audit-s3-public-access

     "I have a bucket named 'my-app-uploads' with BPA off and this policy:
     {Effect: Allow, Principal: '*', Action: 's3:GetObject', Resource:
     'arn:aws:s3:::my-app-uploads/*'}. Is it public?"
```

**Expected behavior:**

1. Applies the classification logic in order (BPA -> policy -> ACL -> condition).
2. Emits VERDICT: PUBLIC (Rule 2: unrestricted wildcard Allow).
3. Cites the severity (HIGH — read-only data exfiltration).
4. Provides specific remediation: enable BPA, restrict/remove policy, use CloudFront OAC.

**CLI routing:**

```bash
node cli/bin/cli.js route "check my S3 buckets for public access"
# [Phase: Audit | Skills routed: s3-public-access-auditor]
```

---

### 3. iam-least-privilege-advisor

**Pipeline phase:** Phase 2 — Audit.

**What it does:** Analyzes AWS IAM policies to identify over-permissive
grants — wildcard actions, wildcard resources, privilege-escalation actions
(PassRole, AssumeRole), inverse wildcards (NotAction/NotResource), and
condition-key bypasses — then provides least-privilege remediation.

**Slash command:** `/aws:audit-iam-least-privilege` — or route via `/aws:pipeline`.

**When to invoke (trigger phrases):**

- "is this IAM policy over-permissive?"
- "check for wildcard permissions"
- "privilege escalation risk"
- "PassRole", "AssumeRole"
- "least privilege", "tighten this role"
- "NotAction", "NotResource"
- auditing a role before production deployment

**Example prompt:**

```
You: "Review this role policy: {Action: 'ec2:*', Resource: '*',
     Effect: Allow}. Is it over-permissive?"
```

**Example invocation:**

```bash
# CLI routing (functional orchestrator)
node cli/bin/cli.js route "is this IAM policy over-permissive"
# [Phase: Audit | Skills routed: iam-least-privilege-advisor]
```

**Expected behavior:**

1. Classifies by the wildcard severity matrix.
2. Emits VERDICT: OVERPERMISSIVE (wildcard actions on wildcard resources).
3. Identifies the specific risk: full EC2 access — can modify security groups, key pairs.
4. Provides scoped-down replacement policy with specific actions/resources.

**End-to-end scenario:** see
[`skills/iam-least-privilege-advisor/examples/end-to-end.md`](skills/iam-least-privilege-advisor/examples/end-to-end.md)
for a multi-statement policy walkthrough (tight read grant + PassRole escalation)
covering aggregation, CRITICAL risk escalation, and the `iam:PassedToService`
condition-key remediation.

---

### 4. ec2-security-group-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ec2-security-groups`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my security groups for open ports"
```

**What it does:** Audits EC2 security group inbound rules to identify publicly
exposed ports and provides remediation guidance mapped to CIS AWS Foundations
Benchmark, PCI-DSS, and NIST SP 800-53. Recognizes port ranges, non-TCP
protocols, managed prefix lists, IPv6 sources, and mixed rule sets.

**When to invoke (trigger phrases):**

- "is this security group open?"
- "check for 0.0.0.0/0 rules"
- "port exposure", "open ports"
- "RDP", "SSH", "3389", "22"
- "database port exposed"
- "CIS benchmark", "PCI-DSS controls"
- reviewing an SG before production deployment

**Example prompt:**

```
You: "My security group sg-xxx has an inbound rule: TCP port 22 from
     0.0.0.0/0. Is this a problem?"
```

**Expected behavior:**

1. Classifies the rule: SSH open to the internet.
2. Emits VERDICT: OPEN (Rule: 0.0.0.0/0 on admin port 22).
3. Maps to CIS AWS Foundations Benchmark 4.1 (ensure no security groups allow ingress from 0.0.0.0/0 to port 22).
4. Provides remediation: restrict to known CIDR, use Session Manager instead.

**End-to-end example:** see `skills/ec2-security-group-auditor/example/end-to-end-audit.md`
for a full four-security-group audit walkthrough (ALB, app-tier, database, and
emergency-access SGs) with orchestrator phase transitions.

---

## Pipeline Walkthrough (end-to-end)

```
You: "/aws:pipeline — I'm onboarding a new account, audit everything."

Orchestrator:
  [Phase: Assess | Resources: starting inventory | Skills routed: all]

  Phase 1 — Assess:
  - s3-public-access-auditor discovers 15 buckets, 3 with BPA off
  - iam-least-privilege-advisor discovers 8 roles, 2 with wildcard actions
  - ec2-security-group-auditor discovers 12 SGs, 4 with 0.0.0.0/0 rules

  [Phase: Audit | Resources: 15 buckets, 8 roles, 12 SGs | Skills routed: all]

  Phase 2 — Audit:
  - s3: 2 PUBLIC (write-open CRITICAL), 1 AMBIGUOUS, 12 SAFE
  - iam: 3 OVERPERMISSIVE, 4 LEAST_PRIVILEGE, 1 AMBIGUOUS
  - ec2: 2 OPEN (SSH+RDP to 0.0.0.0/0), 2 PUBLIC_NONCRITICAL, 8 RESTRICTED

  [Phase: Prioritize | Findings: 2 CRITICAL, 5 HIGH, 2 MEDIUM | Skills routed: orchestrator]

  Phase 3 — Prioritize:
  1. CRITICAL: S3 write-open bucket (data destruction risk) — fix NOW
  2. CRITICAL: S3 write-open bucket #2 — fix NOW
  3. HIGH: SSH open to internet (CIS 4.1) — fix today
  4. HIGH: RDP open to internet (CIS 4.2) — fix today
  5. HIGH: IAM PassRole on * (privilege escalation) — fix today
  ...

  [Phase: Remediate | Findings: 2 CRITICAL prioritized | Skills routed: s3-public-access-auditor]

  Phase 4 — Remediate:
  - S3 CRITICAL: enable BPA immediately (incident response), then audit CloudTrail
  - EC2: restrict SSH/RDP to known CIDR or use Session Manager
  - IAM: scope down PassRole to specific role ARNs
```

---

## Eval Status

Each skill carries a co-located eval specification (`eval/test-cases.yaml`)
and a committed LLM-judge scorecard (`eval/scorecards/<skill>.json`). Run the
assertion layer:

```bash
python3 eval/run_eval.py --assertion-only
```

Run the full LLM-judge eval locally (requires AWS SSO):

```bash
python3 eval/run_eval.py --profile default
```

See [docs/skill-judge-dashboard.md](docs/skill-judge-dashboard.md) for the
per-skill scorecard dashboard.
