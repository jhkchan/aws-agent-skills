# Routing Logic — Reference

Loaded on demand by the orchestrator when a query is ambiguous or spans
multiple skills.

## Single-skill routes (high-confidence)

| Trigger phrase / pattern | Skill |
|---|---|
| "S3", "bucket", "BPA", "Block Public Access", "bucket policy", "ACL", "AllUsers", "AuthenticatedUsers", "Principal:*", "s3:GetObject", "public read", "public write", "s3 exposure", "data leak", "bucket security" | s3-public-access-auditor |
| "IAM", "policy", "role", "least privilege", "wildcard", "PassRole", "AssumeRole", "NotAction", "NotResource", "privilege escalation", "over-permissive", "action:*", "resource:*", "permission boundary", "managed policy", "inline policy" | iam-least-privilege-advisor |
| "security group", "SG", "EC2", "inbound rule", "port exposure", "0.0.0.0/0", "CIDR", "open port", "RDP", "SSH", "3389", "22", "database port", "3306", "5432", "1433", "Redis", "6379", "CIS benchmark", "PCI-DSS", "NIST" | ec2-security-group-auditor |

## Multi-skill / sequential routes

| User goal | Route order |
|---|---|
| Full account security posture audit | Assess (all skills, discovery) -> Audit (all skills) -> Prioritize (orchestrator) -> Remediate (all skills) |
| New account onboarding baseline | Assess (s3 + iam + ec2 discovery) -> Audit (all) -> Prioritize |
| Incident response (suspected breach) | Audit (s3 first if data exposure, iam if credential compromise, ec2 if network intrusion) -> Remediate (immediate containment) -> Audit (re-verify) |
| Compliance audit (CIS/PCI-DSS) | Audit (ec2-sg for CIS controls, iam for access management, s3 for data protection) -> Prioritize (map to control IDs) -> Remediate |
| Pre-production review | Assess (inventory) -> Audit (all) -> Remediate (fix before go-live) |
| Cost + security review | Audit (all skills) -> Prioritize (rank by cost-impact of exposure) |

## Phase-based routing

| Phase | What the user is doing | Route to |
|---|---|---|
| Assess | "what do I have?", "list my resources", "inventory check" | All skills in discovery mode; orchestrator builds inventory |
| Audit | "is this secure?", "check this", "audit this", "what's the verdict?" | Matched specialist for VERDICT |
| Prioritize | "what should I fix first?", "rank these", "which is most critical?" | Orchestrator ranks cross-service findings |
| Remediate | "fix this", "how do I remediate?", "generate fix commands" | Matched specialist's remediation section |

## Disambiguation question templates

Use AskUserQuestion with at most 4 options + "Other".

**Template 1: Service scope**
> "Which AWS service are you auditing?"
> - S3 buckets (public access, BPA, policies) -> s3-public-access-auditor
> - IAM roles/policies (least privilege, wildcards) -> iam-least-privilege-advisor
> - EC2 security groups (open ports, CIDR rules) -> ec2-security-group-auditor
> - All of the above (full audit) -> multi-skill route

**Template 2: Audit depth**
> "How deep do you want to go?"
> - Quick check (just the verdict) -> matched specialist
> - Full audit (verdict + remediation plan) -> specialist + Remediate phase
> - Compliance mapping (CIS/PCI-DSS controls) -> specialist + Prioritize phase
> - Baseline inventory (what exists) -> Assess phase

**Template 3: Finding response**
> "You have findings — what do you want to do?"
> - Show me the full prioritized list -> Prioritize phase
> - Fix the most critical first -> Remediate phase (CRITICAL only)
> - Generate all remediation commands -> Remediate phase (all)
> - Export findings for a report -> Prioritize + format

## When to skip routing

- Query is purely conceptual ("what's the difference between BPA and an ACL?")
  -> answer directly, optionally suggest the relevant skill.
- User has already declared the skill ("use s3-public-access-auditor on this
  bucket") -> route immediately, skip triage.
- Query is outside AWS CloudOps domain ("help me with my Kubernetes cluster")
  -> route outside this suite.

## In-domain, no-skill-matches: decompose + route to nearest skills

**Trigger condition:** the query is in the AWS CloudOps domain (mentions AWS
resources, security, compliance, auditing) BUT no single skill's trigger
pattern exhaustively covers the request.

Examples:
- "Audit my Lambda function's execution role" (Lambda not yet skilled)
- "Check my CloudFront distribution for WAF protection" (CloudFront not yet skilled)
- "Review my RDS instance for public access" (RDS not yet skilled)
- "Audit my KMS key rotation policy" (KMS not yet skilled)

**Procedure (5 steps):**

1. **Decompose** the request into audit sub-tasks.
2. **Match each sub-task** to the nearest existing skill.
3. **Label confidence** per match: `high` / `medium` / `low`.
4. **Caveat statement:** explicitly state "no dedicated skill covers this
   service yet; routing nearest partial matches" BEFORE listing routes.
5. **Out-of-suite handoff:** if no partial match exists, recommend the
   contributor backlog and log a skill-gap candidate.

**Refuse-and-log condition:** if fewer than 2 partial matches can be
identified, refuse politely AND append a `## Skill-gap candidate:` entry to
`cloudops_state.md`. Suggest the user file an issue or propose a new skill.

### Worked example

```
Query: "Audit my CloudFront distribution for WAF and TLS"

Decomposition:
- WAF protection check (is a Web ACL attached?)     -> ec2-security-group-auditor (low — SG is network, not CDN)
- TLS version check (is the minimum TLS >= 1.2?)     -> NO MATCH (new skill needed)
- Origin access control (is the S3 origin private?) -> s3-public-access-auditor (medium — OAC pattern is in S3 remediation)
- Logging enabled (are access logs on?)             -> NO MATCH (new skill needed)

Routing decision:
  No dedicated CloudFront skill exists yet. 1 partial match:
  -> s3-public-access-auditor (medium — can check origin OAC if origin is S3).
  TLS version and logging checks are out-of-suite. Recommend filing a
  skill-gap candidate for cloudfront-distribution-auditor.
```

### Skill-gap candidate logging

When a query gets 0-1 nearest matches, append to `cloudops_state.md`:

```
## Skill-gap candidate: <one-line query summary>
- Query: "<verbatim user query>"
- Date: <ISO date>
- Considered skills: <none, or list of <2 partial matches>
- Recommendation: file an issue or propose a new skill (<service>-<audit-type>)
```
