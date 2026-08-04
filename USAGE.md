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
| `/aws:audit-wafv2-web-acl` | 2 Audit | Audit WAFv2 Web ACLs for default-action posture, managed-rule coverage, COUNT-mode paralysis, shadow rules, and logging gaps |
| `/aws:triage-accessanalyzer-findings` | 2 Audit | Triage IAM Access Analyzer findings (external access + unused access) into risk verdicts — emits VERDICT per finding |
| `/aws:audit-secretsmanager-rotation` | 2 Audit | Audit Secrets Manager secrets for rotation health, Lambda wiring, staleness, and recovery-window state |
| `/aws:triage-guardduty-findings` | 3 Prioritize | Triage GuardDuty findings into context-aware severity (CRITICAL/HIGH/MEDIUM/LOW/LIKELY_FALSE_POSITIVE) with false-positive detection |
| `/aws:audit-kms-key-policy` | 2 Audit | Audit KMS key policies for cross-account decrypt, wildcard kms:*, rotation gaps, deletion-window exposure (routes to `kms-key-policy-auditor`) |
| `/aws:audit-sts-cross-account-role` | 2 Audit | Audit IAM role trust policies for cross-account/external trust, wildcard Principal, and confused-deputy risk (routes to `sts-cross-account-role-auditor`) |
| `/aws:audit-inspector2-coverage-findings` | 2 Audit | Audit Inspector2 coverage gaps + finding severity — CRITICAL/HIGH/MEDIUM/LOW/COVERED per resource (routes to `inspector2-coverage-finding-auditor`) |
| `/aws:audit-cognito-user-pool` | 2 Audit | Audit Cognito user pools for MFA, password policy, auth-flow safety, OAuth exposure, ASF mode — emits INSECURE/WEAK/ADEQUATE/OK per pool (routes to `cognito-idp-user-pool-auditor`) |
| `/aws:audit-acm-certificate-expiry` | 2 Audit | Audit ACM certificates for expiry, renewal status, and key-algorithm compliance — emits VERDICT per certificate (routes to `acm-certificate-expiry-auditor`) |
| `/aws:audit-securityhub-control-compliance` | 2 Audit | Audit Security Hub control findings — classifies lifecycle states (suppressed, resolved, archived, NOT_AVAILABLE) into FAILED/WARNING/PASSED/NOT_APPLICABLE + maps to fix action (routes to `securityhub-control-compliance-auditor`) |

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

### 5. kms-key-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-kms-key-policy`

**What it does:** Audits KMS key policies and key metadata for cross-account
or external principal access, wildcard `kms:*` grants, the `kms:Decrypt`
blast-radius multiplier, `kms:CreateGrant` delegation vectors, automatic-key-
rotation status, and key-deletion window exposure. Emits a deterministic
severity verdict (CRITICAL | HIGH | MEDIUM | OK) per key with enumerated
findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this KMS key policy"
- "check for cross-account KMS decrypt"
- "kms wildcard permissions"
- "is key rotation enabled?"
- "key pending deletion"
- "kms:CreateGrant delegation"
- "kms blast radius"
- reviewing a KMS key before production deployment

**Example prompt:**

```
You: "This KMS key grants kms:Decrypt to arn:aws:iam::222222222222:role/external
     with no condition. Rotation is off. What's the risk?"
```

**Expected behavior:**

1. Classifies the principal scope (cross-account), action danger
   (DATA_ACCESS — Decrypt is a blast-radius multiplier), and condition
   strength (none).
2. Emits VERDICT: CRITICAL (Rule 5c — cross-account decrypt, no condition).
3. Identifies the rotation gap as an additional HIGH finding.
4. Provides assume-breach remediation: remove the grant, audit CloudTrail
   for decrypt events, re-encrypt affected data, enable rotation.

**End-to-end scenario:** see
[`skills/kms-key-policy-auditor/examples/end-to-end.md`](skills/kms-key-policy-auditor/examples/end-to-end.md)
for a multi-statement key policy walkthrough (root trust + cross-account
decrypt + same-account ViaService) covering severity aggregation, the
root-of-trust exception, and the assume-breach remediation workflow.

---

### 6. sts-cross-account-role-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-sts-cross-account-role`

**What it does:** Audits IAM role trust policies
(AssumeRolePolicyDocument) for cross-account/external trust exposure,
wildcard Principal grants, confused-deputy service-principal vectors, and
condition-strength weaknesses. Emits a deterministic
EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK verdict per role.

**When to invoke (trigger phrases):**

- "who can assume this role?"
- "audit this role trust policy"
- "cross-account role trust"
- "confused deputy", "confused-deputy risk"
- "ExternalId missing"
- "Principal star", "Principal wildcard"
- "service principal trust"
- "SourceArn missing", "SourceAccount condition"
- "SAML federated trust"
- "NotPrincipal trust policy"
- hardening a role trust before production

**Example prompt:**

```
You: "Audit this role's trust policy before we deploy. Role ARN:
     arn:aws:iam::123456789012:role/data-pipeline-access.
     Trust policy: {Principal: {Service: lambda.amazonaws.com},
     Action: sts:AssumeRole}. Is this safe?"
```

**Expected behavior:**

1. Classifies by the 9-step trust-policy decision tree.
2. Emits VERDICT: EXTERNAL_TRUST (Step 4: confused-deputy service principal
   without aws:SourceArn/aws:SourceAccount).
3. Explains the confused-deputy problem: any AWS customer's Lambda function
   can trigger an AssumeRole call via the Lambda service.
4. Provides specific remediation: add aws:SourceArn (ArnLike) +
   aws:SourceAccount (StringEquals) condition.

**End-to-end scenario:** see
[`skills/sts-cross-account-role-auditor/examples/end-to-end.md`](skills/sts-cross-account-role-auditor/examples/end-to-end.md)
for a multi-statement trust-policy walkthrough (same-account CI trust +
unguarded Lambda service principal) covering aggregation, confused-deputy
detection, and the dual SourceArn + SourceAccount remediation.

**Relationship to iam-least-privilege-advisor:** This skill audits the
**trust policy** (who can assume the role). The iam-least-privilege-advisor
audits the **permissions policy** (what the role can do after assuming it).
Both surfaces should be audited for every role.

---

### 7. inspector2-coverage-finding-auditor

**Pipeline phase:** Phase 2 — Audit.

**What it does:** Audits Amazon Inspector2 coverage gaps and finding severity
to determine whether EC2 instances, ECR repositories, and Lambda functions are
effectively scanned and free of exploitable vulnerabilities or
misconfigurations. Classifies each resource into a single
CRITICAL / HIGH / MEDIUM / LOW / COVERED verdict by reasoning over Inspector2
enablement state, per-resource coverage status (SSM-agent dependency for EC2,
scanOnPush for ECR, Lambda code-scanning opt-in), network-reachability
amplification of CVEs, CISA KEV catalog cross-reference, finding lifecycle
(OPEN vs SUPPRESSED), and resource criticality tier.

**Slash command:** `/aws:audit-inspector2-coverage-findings` — or route via `/aws:pipeline`.

**When to invoke (trigger phrases):**

- "are my EC2 instances covered by Inspector2?"
- "what's the severity of these findings?"
- "is this CVE internet-reachable?"
- "check scan coverage before production deployment"
- "SSM agent offline — coverage gap"
- "ECR scanOnPush audit"
- "Lambda code scanning disabled"
- "KEV catalog check"
- "vulnerability posture audit"

**Example prompt:**

```
You: "I have an EC2 instance i-prod-web-01 with an OPEN CRITICAL CVE
     (CVE-2021-44228, log4j) and a NETWORK_REACHABILITY finding showing port
     443 is reachable from the internet. Coverage is ACTIVE. How bad is this?"
```

**Expected behavior:**

1. Applies the 8-step classification logic (coverage -> finding -> aggregation).
2. Emits VERDICT: CRITICAL (internet-reachable critical CVE = confirmed exploitable).
3. Cites the reachability amplification rule and CISA KEV catalog cross-reference.
4. Provides containment-first remediation (restrict SG, then patch via SSM).

**End-to-end scenario:** see
[`skills/inspector2-coverage-finding-auditor/examples/end-to-end.md`](skills/inspector2-coverage-finding-auditor/examples/end-to-end.md)
for a four-resource walkthrough (internet-reachable critical CVE, SSM-offline
coverage gap, Lambda partial coverage, clean ECR) covering reachability
amplification, coverage-tier classification, and account-level aggregation.

---

### 8. guardduty-finding-severity-triage

**Pipeline phase:** Phase 3 — Prioritize.

**Slash command:** `/aws:triage-guardduty-findings`

**What it does:** Classifies Amazon GuardDuty findings into a context-aware
triage severity (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) by
overlaying finding-type threat taxonomy, six false-positive detection
patterns, aggregation counts, and resource criticality on top of
GuardDuty's numeric severity. Flags authorized-scanner port sweeps,
Tor traffic on public-facing services, known-safe DNS domains, and AWS
service-linked role activity as likely false positives.

**When to invoke (trigger phrases):**

- "triage this GuardDuty finding"
- "is this finding a false positive?"
- "GuardDuty severity classification"
- "PortSweepUnusual", "TorIPCaller", "CryptocurrencyClient"
- "SSHBruteForce", "MaliciousIPCaller"
- "should I archive this finding?"
- "suppression filter"
- prioritizing findings for a SOC queue

**Example prompt:**

```
You: /aws:triage-guardduty-findings

     "Finding type: Impact:EC2/CryptocurrencyClient!SSH, Severity: 8.0,
     Resource: i-0prodweb9988, Count: 12. Triage this."
```

**Expected behavior:**

1. Checks false-positive patterns first (authorized scanner, known-safe
   DNS, expected Tor on public service, AWS service role, change window).
2. If not a false positive, classifies by threat category: crypto mining /
   credential exfiltration / confirmed C2 -> CRITICAL; brute force /
   malicious IP / backdoor -> HIGH; behavioral anomaly -> MEDIUM; port
   probe / recon -> LOW.
3. Applies context overlays (count > 50 escalation, resource criticality).
4. Emits VERDICT with specific remediation (IR steps for CRITICAL,
   archival + suppression filter for LIKELY_FALSE_POSITIVE).

**End-to-end scenario:** see
[`skills/guardduty-finding-severity-triage/example/end-to-end.md`](skills/guardduty-finding-severity-triage/example/end-to-end.md)
for a three-finding batch triage walkthrough (CRITICAL crypto mining,
LIKELY_FALSE_POSITIVE scanner, MEDIUM anomalous login) covering
false-positive override, threat-category escalation, and forensic-first
remediation ordering.

---

### 9. cognito-idp-user-pool-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cognito-user-pool`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my Cognito user pool for security"
```

**What it does:** Audits Amazon Cognito user pool configurations for
identity-security posture — MFA enforcement (OFF/OPTIONAL/ON), password
policy strength, app-client auth-flow safety (SRP vs password vs admin),
OAuth flow exposure (implicit vs code+PKCE), token validity,
PreventUserExistenceErrors (user enumeration), Advanced Security Features
mode (OFF/AUDIT/ENFORCED), and deletion protection. Recognizes the
`ADMIN_NO_SRP_AUTH` / `ALLOW_ADMIN_USER_PASSWORD_AUTH` rename, SMS-vs-TOTP
MFA risk, and multi-client aggregation (worst-client-wins).

**When to invoke (trigger phrases):**

- "is this Cognito user pool secure?"
- "check MFA enforcement"
- "audit my app client auth flows"
- "is the OAuth configuration safe?"
- "PreventUserExistenceErrors"
- "implicit flow vs code flow"
- "ALLOW_ADMIN_USER_PASSWORD_AUTH"
- "harden this pool before production"
- reviewing a user pool before production deployment

**Example prompt:**

```
You: "Audit this Cognito pool: MfaConfiguration OFF, password 6 chars no
     complexity, app client uses USER_PASSWORD_AUTH with no secret,
     PreventUserExistenceErrors LEGACY. Is this production-ready?"
```

**Expected behavior:**

1. Classifies the pool: no MFA + weak password + user enumeration + public
   client with password auth.
2. Emits VERDICT: INSECURE (Rule 1a + 1c + 1d — CRITICAL).
3. Identifies the specific risks: account takeover via brute-force,
   user enumeration, credential capture via non-SRP flow.
4. Provides ordered remediation: enable MFA (phased), fix OAuth flows,
   enable PreventUserExistenceErrors, migrate to SRP auth.

**End-to-end scenario:** see
[`skills/cognito-idp-user-pool-auditor/example/end-to-end-audit.md`](skills/cognito-idp-user-pool-auditor/example/end-to-end-audit.md)
for a three-config walkthrough (INSECURE pool with implicit OAuth + legacy
errors, WEAK pool with admin auth flow, fully hardened OK pool) covering
multi-client aggregation, auth-flow strength matrix reasoning, and phased
MFA rollout remediation.

---

### 9. acm-certificate-expiry-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-acm-certificate-expiry`

**CLI route:**

```bash
node cli/bin/cli.js route "check my ACM certificates for expiry"
```

**What it does:** Audits ACM certificates for expiry risk, renewal status
(FAILED_AUTORENEWAL, auto-renewal eligibility), certificate type (AMAZON_ISSUED
vs IMPORTED), validation method (DNS vs email), and key-algorithm strength
(RSA_2048, EC, deprecated RSA_1024). Classifies each certificate into a
deterministic verdict: EXPIRED, EXPIRING_SOON, RENEWAL_FAILED, or OK.

**When to invoke (trigger phrases):**

- "is this certificate about to expire?"
- "ACM certificate renewal failed"
- "FAILED_AUTORENEWAL", "CAA_ERROR"
- "imported certificate expiry"
- "DNS validation CNAME deleted"
- "certificate key algorithm", "RSA_1024"
- "CloudFront certificate region"
- "TLS certificate health", "certificate compliance"
- auditing certificates before production deployment

**Example prompt:**

```
You: "My ACM certificate for api.example.com has NotAfter 2026-07-15
     and Status EXPIRED. What's the impact and how do I fix it?"
```

**Expected behavior:**

1. Computes days_until_expiry from NotAfter (UTC).
2. Checks Status (EXPIRED → terminal), RenewalSummary (FAILED_AUTORENEWAL →
   renewal failure), and Type (IMPORTED uses 60-day threshold vs 30-day for
   AMAZON_ISSUED).
3. Emits VERDICT with risk level and specific remediation (CAA record fix,
   CNAME re-creation, re-import command, re-request with DNS validation).
4. Flags deprecated key algorithms (RSA_1024) even when verdict is OK.

**End-to-end example:** see
[`skills/acm-certificate-expiry-auditor/examples/end-to-end.md`](skills/acm-certificate-expiry-auditor/examples/end-to-end.md)
for a three-certificate audit walkthrough (EXPIRED, RENEWAL_FAILED via CAA_ERROR,
and IMPORTED EXPIRING_SOON) covering type-aware thresholds and CAA-root-cause
diagnosis.

---

### 10. secretsmanager-rotation-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-secretsmanager-rotation` — or route via `/aws:pipeline`.

**What it does:** Audits Secrets Manager secrets for rotation health —
rotation enablement, rotation-Lambda health (existence, execution-role
permissions, VPC connectivity, invocation errors), staleness against the
configured rotation interval, stuck AWSPENDING versions, and recovery-window
state. Classifies each secret as UNROTATED, ROTATION_BROKEN, STALE, or OK
with risk-severity and concrete remediation.

**When to invoke (trigger phrases):**

- "is this secret rotating?"
- "check secret rotation health"
- "rotation Lambda broken"
- "stale secret", "unrotated secret"
- "LastRotatedDate", "AutomaticallyAfterDays"
- "AWSPENDING stuck version"
- "recovery window secret"
- "credential hygiene", "rotation compliance"
- reviewing secret rotation before a compliance gate

**Example prompt:**

```
You: "This RDS secret has RotationEnabled: true but LastRotatedDate is null
     and the rotation Lambda errors with ResourceNotFoundException (DB deleted).
     Is the credential being rotated?"
```

**Expected behavior:**

1. Applies the 8-step classification in dependency-chain order (recovery
   window -> rotation enabled -> Lambda existence -> Lambda invocation ->
   execution-role chain -> AWSPENDING -> freshness -> OK).
2. Emits VERDICT: ROTATION_BROKEN (Step 7a — null LastRotatedDate after
   3 intervals, Lambda erroring on deleted target).
3. Cites the root cause: target RDS instance deleted, Lambda cannot complete
   setSecret step.
4. Provides specific remediation: recreate or retarget the Lambda, then
   trigger manual rotation to verify.

**End-to-end scenario:** see
[`skills/secretsmanager-rotation-auditor/example/README.md`](skills/secretsmanager-rotation-auditor/example/README.md)
for a three-secret audit walkthrough (UNROTATED RDS, ROTATION_BROKEN with
deleted Lambda, OK healthy rotation) covering the full dependency-chain
analysis and remediation workflow.

---

### 11. securityhub-control-compliance-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-securityhub-control-compliance` — or route via `/aws:pipeline`.

**What it does:** Audits AWS Security Hub control compliance findings and maps
each to a deterministic verdict (FAILED | WARNING | PASSED | NOT_APPLICABLE),
then maps every FAILED / WARNING control to a specific fix action. Handles the
full finding lifecycle — active findings, suppressed failures, resolved-but-
still-failing, archived findings, NOT_AVAILABLE with StatusReasons splitting,
and multi-account aggregation across FSBP / CIS / PCI-DSS / NIST 800-53
standards.

**When to invoke (trigger phrases):**

- "security hub compliance status"
- "triage these security hub findings"
- "is this control failing or just suppressed?"
- "NOT_AVAILABLE finding — does it apply?"
- "StatusReasons code"
- "FSBP control", "CIS benchmark control"
- "compliance gap report"
- "fix action for this control"
- preparing for a quarterly compliance review or audit

**Example prompt:**

```
You: "This Security Hub finding for EC2.15 has Compliance.Status FAILED but
     Workflow.Status SUPPRESSED with no note. What's the real compliance
     posture?"
```

**Expected behavior:**

1. Applies the 8-step classification in lifecycle order (ARCHIVED -> SUPPRESSED
   -> RESOLVED -> NOT_AVAILABLE split -> FAILED -> WARNING -> PASSED).
2. Emits VERDICT: WARNING (Rule 2 — suppressed FAILED is a governance concern,
   not a pass).
3. Identifies the missing suppression note and the stale age (>60 days).
4. Provides specific remediation: review the suppression, unsuppress if the
   compensating control is no longer valid, then restrict the SG rule.

**End-to-end scenario:** see
[`skills/securityhub-control-compliance-auditor/example/end-to-end-audit.md`](skills/securityhub-control-compliance-auditor/example/end-to-end-audit.md)
for a five-finding audit walkthrough covering all four verdicts (FAILED, PASSED,
NOT_APPLICABLE, WARNING) with aggregate rollup and the full remediation workflow.

---

### 12. wafv2-web-acl-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-wafv2-web-acl`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my WAF web acl"
```

**What it does:** Audits WAFv2 Web ACL configurations to determine whether the
ACL provides effective protection: default-action posture (Allow vs Block),
managed-rule-group coverage gaps, rule effectiveness (BLOCK vs COUNT, shadow
rules, stale exclusions), rate-based rule correctness, logging and visibility
configuration, and text-transformation bypass vectors. Emits a deterministic
verdict (MISCONFIGURED | WEAK | ADEQUATE | OK) per Web ACL.

**When to invoke (trigger phrases):**

- "audit my WAF"
- "WAFv2 web acl"
- "check managed-rule coverage"
- "are my WAF rules in count mode?"
- "shadow rule bypass"
- "rate-based rule behind CloudFront"
- "WAF logging"
- "OWASP WAF", "hardening WAF before production"
- reviewing a WAF before production deployment

**Example prompt:**

```
You: "Audit this WAF before we go to production. DefaultAction is Allow,
     CommonRuleSet and SQLiRuleSet are in BLOCK, but there's a custom
     Allow rule at priority 0 matching /api/."
```

**Expected behavior:**

1. Applies the 11-step classification logic in declaration order.
2. Emits VERDICT: MISCONFIGURED (Step 2: shadow rule bypasses managed
   inspection for all /api/ traffic).
3. Cites the priority-ordering bypass and the compound gaps (no rate rule,
   no logging).
4. Provides specific remediation: reprioritize the shadow rule, add a
   FORWARDED_IP rate-based rule, enable logging.

**End-to-end example:** see
[`skills/wafv2-web-acl-auditor/examples/end-to-end.md`](skills/wafv2-web-acl-auditor/examples/end-to-end.md)
for a shadow-bypass-rule walkthrough covering priority-ordering analysis,
COUNT-mode detection, and the safe BLOCK-mode progression.

---

### 13. accessanalyzer-finding-triage

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:triage-accessanalyzer-findings` — or route via `/aws:pipeline`.

**What it does:** Triages IAM Access Analyzer findings (external access +
unused access) into risk verdicts with remediation. Classifies each finding as
EXTERNAL_ACCESS (real exposure), UNUSED_ACCESS (stale identity/credential),
EXPECTED (known cross-account or service integration), or SAFE (condition-
bounded non-risk). Evaluates the zone-of-trust model, principal type (public
vs specific vs service), condition-key cryptographic strength, resource-type
blast radius, and finding freshness.

**When to invoke (trigger phrases):**

- "triage this Access Analyzer finding"
- "is this external access finding a real risk?"
- "should I archive this finding?"
- "unused IAM role", "unused access key"
- "isPublic finding"
- "zone of trust", "cross-account resource policy"
- "service principal finding"
- "is this cross-account access expected?"
- "archive rule suppression"

**Example prompt:**

```
You: /aws:triage-accessanalyzer-findings

     "Finding type: ExternalAccess, Resource: AWS::KMS::Key,
     Principal: '*', isPublic: true, Actions: kms:Decrypt,
     Condition: {}. What's the risk?"
```

**Expected behavior:**

1. Routes by finding type (ExternalAccess vs Unused*).
2. For external access: evaluates condition strength (cryptographic vs
   forgeable), classifies principal type, applies resource-type severity
   matrix, checks expected service integrations.
3. Emits VERDICT: EXTERNAL_ACCESS / CRITICAL (KMS decrypt is a data-access
   multiplier).
4. Provides incident-response remediation with CloudTrail audit for the
   exposure window.

**End-to-end example:** see
[`skills/accessanalyzer-finding-triage/example/README.md`](skills/accessanalyzer-finding-triage/example/README.md)
for a four-finding batch triage walkthrough (KMS public CRITICAL, S3
condition-bounded SAFE, unused stale role, Lambda service principal EXPECTED)
covering condition-strength classification, service-integration recognition,
and prioritized remediation.

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
