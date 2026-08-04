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
| `/aws:audit-ecs-task-definition` | 2 Audit | Audit ECS task definitions for privileged containers, plaintext secrets in env vars, host network mode, root-user execution, missing resource limits — emits PRIVILEGED/SECRET_LEAK/INSECURE/CONFIG_GAP/OK per task (routes to `ecs-task-definition-auditor`) |
| `/aws:audit-backup-plan` | 2 Audit | Audit AWS Backup plans for coverage gaps, vault risks (no lock, governance-mode lock, AWS-managed key), impossible lifecycle configs, and compliance violations — emits COVERAGE_GAP/VAULT_RISK/NONCOMPLIANT/CONFIG_GAP/OK per plan (routes to `backup-plan-auditor`) |
| `/aws:audit-eks-cluster` | 2 Audit | Audit EKS clusters for public API endpoint, disabled control-plane logging, IAM auth mapRoles, security group exposure, and outdated version (routes to `eks-cluster-auditor`) |
| `/aws:audit-compute-optimizer-findings` | 2 Audit | Audit Compute Optimizer findings for EC2/EBS/Lambda/ASG — confidence-gated UNDERUTILIZED/NOT_OPTIMIZED/OK with per-finding risk + CLI remediation (routes to `compute-optimizer-findings-auditor`) |
| `/aws:audit-lambda-runtime-deprecation` | 2 Audit | Audit Lambda functions for deprecated/EOL runtimes, over-permissioned execution roles, public function URL exposure, and observability config gaps — emits VERDICT per function (routes to `lambda-runtime-deprecation-auditor`) |
| `/aws:audit-autoscaling-group` | 2 Audit | Audit Auto Scaling Groups for launch-template health, ELB health-check integrity, mixed-instances Spot diversification, capacity bounds, and unhealthy-termination behavior — emits MISCONFIGURED/CONFIG_GAP/OK per ASG (routes to `autoscaling-group-auditor`) |
| `/aws:audit-ecr-repository` | 2 Audit | Audit ECR private repositories for public access, scan-on-push gaps, lifecycle-policy absence, tag-immutability gaps, unscanned images — emits PUBLIC/NO_SCAN/NO_LIFECYCLE/CONFIG_GAP/OK per repo (routes to `ecr-repository-auditor`) |
| `/aws:audit-efs-filesystem` | 2 Audit | Audit EFS filesystems for encryption-at-rest, public filesystem policy, TLS enforcement, lifecycle management, and access point governance — emits UNENCRYPTED/PUBLIC_POLICY/CONFIG_GAP/OK per filesystem (routes to `efs-filesystem-auditor`) |
| `/aws:audit-dlm-lifecycle-policy` | 2 Audit | Audit DLM EBS snapshot lifecycle policies for disabled state, empty tag/resource targets, invalid schedules, weak retention, missing cross-region copy (DR gap), CopyTags metadata loss, and per-volume snapshot quota risk — emits NO_POLICY/MISCONFIGURED/CONFIG_GAP/OK per policy (routes to `dlm-lifecycle-policy-auditor`) |
| `/aws:audit-ebs-volume` | 2 Audit | Audit EBS volumes and snapshots for unencrypted state, unattached cost waste, legacy gp2/io1/standard volume types (gp3/io2 upgrade), stale snapshots (with FSR cost-dominance check), and public-snapshot block-data exposure — emits UNENCRYPTED/UNATTACHED/LEGACY_TYPE/STALE_SNAPSHOT/PUBLIC_SNAPSHOT/OK per resource (routes to `ebs-volume-auditor`) |
| `/aws:audit-budgets` | 2 Audit | Audit AWS Budgets for cost-overrun blind spots — zero budgets, decorative budgets (no notifications), SNS topic policies that silently block delivery (missing budgets.amazonaws.com publish), single-threshold/no-forecast alerts, breached or on-track-to-breach spend, and missing zero-spend guardrails for new accounts — emits NO_BUDGET/NO_ALERT/CONFIG_GAP/OK per account (routes to `budgets-auditor`) |
| `/aws:audit-route53-records` | 2 Audit | Audit Route 53 records for missing health checks on weighted/failover/latency routing, dangling ALIAS targets, DNSSEC gaps, public-zone private-IP exposure, TTL inconsistency — emits NO_HEALTH_CHECK/DNSSEC_GAP/DANGLING/CONFIG_GAP/OK per record (routes to `route53-record-auditor`) |
| `/aws:audit-cur-cost-usage-report` | 2 Audit | Audit Cost and Usage Report (CUR) for coverage, staleness, report version, Athena integration, S3 versioning, and time-horizon health — emits NO_CUR/STALE/CONFIG_GAP/OK per report (routes to `cur-cost-usage-report-auditor`) |
| `/aws:audit-cost-optimization-hub` | 2 Audit | Audit Cost Optimization Hub for recommendation enablement, member-account coverage, effort-level distribution, and stale high-value unactioned recommendations — emits DISABLED/NO_MEMBER_ACCOUNTS/HIGH_EFFORT/CONFIG_GAP/OK per account (routes to `cost-optimization-hub-recommendations-auditor`) |
| `/aws:audit-billing-account` | 2 Audit | Audit AWS account billing posture — root MFA and access keys, IAM user/group billing access delegation, Cost Anomaly Detection enablement, billing budgets, and free-tier usage alerts — emits ROOT_BILLING/NO_ANOMALY_DETECTION/CONFIG_GAP/OK per account (routes to `billing-account-auditor`) |
| `/aws:audit-ce-cost-anomaly` | 2 Audit | Audit Cost Explorer anomaly-detection subscriptions (monitor type, subscription frequency, threshold calibration), RI/SP commitment coverage gaps on steady-state compute, idle-resource detection readiness (CUR resource-ID gating), and report-subscription cadence (IMMEDIATE vs WEEKLY mismatch) — emits NO_ANOMALY_SUB/LOW_RI_COVERAGE/CONFIG_GAP/OK per account (routes to `ce-cost-anomaly-auditor`) |
| `/aws:audit-elbv2-load-balancer` | 2 Audit | Audit ALB/NLB for insecure TLS listener policies (TLS 1.0/1.1, weak ciphers), disabled access logs, permissive security groups, idle load balancers (no targets), disabled cross-zone (NLB), and missing deletion protection — emits INSECURE_LISTENER/NO_ACCESS_LOGS/PERMISSIVE_SG/IDLE/CONFIG_GAP/OK per LB (routes to `elbv2-load-balancer-auditor`) |
| `/aws:audit-networkmanager-core-network` | 2 Audit | Audit Network Manager (Cloud WAN) core networks for detached attachments, permissive resource/segment policies, CIDR overlap, and LATEST-vs-LIVE policy mismatch — emits DETACHED_ATTACHMENT/PERMISSIVE_POLICY/CIDR_OVERLAP/CONFIG_GAP/OK per core network (routes to `networkmanager-core-network-auditor`) |
| `/aws:audit-directconnect-topology` | 2 Audit | Audit Direct Connect topology for single-path failure risk (same-POP pseudo-diversity), MACSec `should_encrypt`/`no_encrypt` on capable hardware, public-VIF BGP MD5 (route-hijack defence), VIF redundancy via DXGW, and LOA-CFA provisioning state — emits SINGLE_CONNECTION/NO_ENCRYPTION/CONFIG_GAP/OK per topology (routes to `directconnect-auditor`) |

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

### 14. ecs-task-definition-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ecs-task-definition`

**What it does:** Audits ECS task definitions for privileged containers,
plaintext secrets in environment variables (instead of Secrets Manager / SSM),
host network mode, root-user execution, and missing resource limits (CPU,
memory, logging). Emits a deterministic verdict
(PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK) per task definition
with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this ECS task definition"
- "is my ECS container privileged?"
- "check ECS task for secrets in env vars"
- "ECS host network mode"
- "is my container running as root?"
- "ECS resource limits missing"
- "harden my Fargate task"
- reviewing a task definition before production deployment

**Example prompt:**

```
You: "This ECS task has privileged: true, DATABASE_PASSWORD in environment,
     and networkMode host. Audit it before we migrate to Fargate."
```

**Expected behavior:**

1. Classifies the privileged flag (PRIVILEGED on EC2 — full host kernel
   access), the plaintext secret (SECRET_LEAK), and the insecure network
   mode + root user (INSECURE).
2. Emits VERDICT: PRIVILEGED (worst finding wins — Step 1).
3. Identifies the secret leak and insecure configuration as additional
   findings.
4. Provides register-new-revision remediation: set privileged: false,
   move secret to secrets array (rotate the credential), change to
   awsvpc network mode, set non-root user, add resource limits.

**End-to-end scenario:** see
[`skills/ecs-task-definition-auditor/examples/end-to-end.md`](skills/ecs-task-definition-auditor/examples/end-to-end.md)
for a multi-finding legacy EC2 task definition walkthrough (privileged +
secret leak + host network + root user + no limits + dangerous
capabilities) covering severity aggregation and the register-new-revision
remediation workflow.

---

### 15. eks-cluster-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-eks-cluster`

**What it does:** Audits AWS EKS cluster configurations for public API
endpoint exposure, disabled control-plane logging, IAM auth mapRoles
misconfiguration (system:masters to broad principals, node IAM role
privilege escalation, wildcard username), security group ingress exposure
on critical ports (kubelet 10250, API 443, SSH 22), and outdated Kubernetes
version drift. Emits a deterministic categorical verdict
(PUBLIC_ENDPOINT | LOGGING_DISABLED | CONFIG_GAP | OUTDATED | OK) per
cluster with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this EKS cluster"
- "is my EKS API server public"
- "check control-plane logging"
- "audit aws-auth ConfigMap"
- "system:masters mapping"
- "check EKS security groups"
- "is my Kubernetes version outdated"
- "harden EKS cluster"
- reviewing an EKS cluster before production deployment or compliance audit

**Example prompt:**

```
You: "Audit this EKS cluster before our compliance review. The API
     endpoint is public with publicAccessCidrs empty, logging is off,
     and the node IAM role is in system:masters. What's the risk?"
```

**Expected behavior:**

1. Applies the priority-ordered classification (endpoint -> logging ->
   config -> version).
2. Emits VERDICT: PUBLIC_ENDPOINT (Step 1 — empty publicAccessCidrs
   defaults to 0.0.0.0/0).
3. Lists all other findings (LOGGING_DISABLED, CONFIG_GAP for node-role
   escalation, OUTDATED if applicable) in the FINDINGS section.
4. Provides specific remediation with CLI commands for each finding.

**End-to-end scenario:** see
[`skills/eks-cluster-auditor/examples/end-to-end.md`](skills/eks-cluster-auditor/examples/end-to-end.md)
for a multi-finding cluster walkthrough (public endpoint, disabled logging,
node-role privesc, open kubelet port, outdated version) covering
priority-ordered classification, the empty-CIDR trap, and the
multi-finding remediation workflow.

---

### 16. lambda-runtime-deprecation-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-lambda-runtime-deprecation`

**What it does:** Audits AWS Lambda functions for deprecated/EOL runtimes
(python3.9, nodejs16.x, etc.), over-permissioned execution roles (admin
wildcards, privilege-escalation actions), public function URL exposure
(AuthType NONE), and observability config gaps (missing X-Ray tracing,
missing DLQ, reserved concurrency 0). Emits a deterministic verdict
(DEPRECATED_RUNTIME | PUBLIC_EXPOSURE | OVERPERMISSIVE | CONFIG_GAP | OK)
per function with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Lambda function"
- "is my Lambda runtime deprecated?"
- "Lambda runtime EOL"
- "check Lambda execution role"
- "Lambda admin role"
- "is my function URL public?"
- "Lambda AuthType NONE"
- "missing X-Ray tracing Lambda"
- "Lambda dead letter queue"
- "hardening Lambda function"
- reviewing a Lambda function before production deployment

**Example prompt:**

```
You: "This Lambda function runs python3.9 with a scoped S3 role, active
     tracing, and no function URL. Is it production-ready?"
```

**Expected behavior:**

1. Compares Runtime (python3.9) against the supported-runtime set.
2. Emits VERDICT: DEPRECATED_RUNTIME (Step 1 — python3.9 is deprecated,
   Phase 1 create/update block in effect; function is a ticking time bomb).
3. Confirms the execution role, tracing, and URL are all OK — the runtime
   is the sole finding.
4. Provides specific remediation: update to python3.12, test code
   compatibility, publish a new version.

**End-to-end scenario:** see
[`skills/lambda-runtime-deprecation-auditor/examples/end-to-end.md`](skills/lambda-runtime-deprecation-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (nodejs16.x blocked Phase 2 + public
function URL) covering worst-finding aggregation, runtime lifecycle phases,
and the stale-LastModified risk amplifier.

---

### 17. compute-optimizer-findings-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-compute-optimizer-findings`

**What it does:** Audits AWS Compute Optimizer findings for EC2, EBS, Lambda,
and Auto Scaling Group resources — classifies overprovisioned (underutilized)
cost waste, underprovisioned (performance-risk) findings, and low-confidence
recommendations (inferred memory without CWAgent, high performanceRisk, stale
findings, zero-invocation Lambda) into a deterministic verdict with per-finding
risk and CLI remediation. Emits UNDERUTILIZED | NOT_OPTIMIZED | OK per resource.

**When to invoke (trigger phrases):**

- "audit compute optimizer findings"
- "check EC2 right-sizing recommendations"
- "is this compute optimizer finding reliable"
- "overprovisioned instances"
- "Lambda memory recommendations"
- "EBS volume recommendations"
- "performanceRisk too high"
- "compute optimizer low confidence"
- "right-size EC2 instances"
- reviewing cost-optimization posture before a batch right-size

**Example prompt:**

```
You: "This EC2 instance has a Compute Optimizer finding of Overprovisioned
     with CPU at 8% and Memory at 15% (CWAgent installed). performanceRisk 1,
     savings $150/month. Should I right-size?"
```

**Expected behavior:**

1. Applies the confidence gate first — checks whether Memory metrics are
   measured (CWAgent present) vs inferred, evaluates performanceRisk, checks
   data sufficiency and staleness.
2. Emits VERDICT: UNDERUTILIZED (Overprovisioned + HIGH confidence + savings
   > $100/month = actionable cost waste).
3. Quantifies waste ($150/month) and risk-tier it HIGH.
4. Provides CLI remediation: create AMI, stop, modify-instance-attribute,
   start, monitor 7 days.

**End-to-end scenario:** see
[`skills/compute-optimizer-findings-auditor/examples/end-to-end.md`](skills/compute-optimizer-findings-auditor/examples/end-to-end.md)
for a two-instance walkthrough (high-confidence UNDERUTILIZED vs low-confidence
NOT_OPTIMIZED with inferred memory) covering confidence gating,
performanceRisk interpretation, and per-resource CLI remediation.

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

### 17. autoscaling-group-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-autoscaling-group`

**What it does:** Audits AWS Auto Scaling Groups for launch-template health
(legacy launch configuration, IMDSv2 enforcement), ELB health-check integrity
(missing target group, grace-period timing), mixed-instances policy (single
Spot instance type, allocation strategy), capacity bounds (desired vs
min/max), and unhealthy-termination behavior (EC2-only checks behind an ELB,
capacity rebalance). Emits a deterministic verdict
(MISCONFIGURED | CONFIG_GAP | OK) per ASG with enumerated findings and
specific remediation.

**When to invoke (trigger phrases):**

- "audit this auto scaling group"
- "is my ASG misconfigured?"
- "why are my instances cycling?"
- "check ASG health check wiring"
- "launch template vs launch configuration"
- "spot single instance type"
- "ASG infinite replacement loop"
- "is my Spot diversification sufficient?"

**Example prompt:**

```
You: "This ASG has HealthCheckType ELB but no target group attached.
     Instances keep cycling. What's wrong?"
```

**Expected behavior:**

1. Classifies the ELB health check as MISCONFIGURED (Step 3) — no target
   group means every instance is Unhealthy from launch, creating an infinite
   replacement loop.
2. Evaluates all other dimensions (launch template IMDSv2, capacity bounds,
   MIP diversification, AZ diversity, scale-out headroom).
3. Emits VERDICT: MISCONFIGURED with per-finding breakdown.
4. Provides specific remediation: attach the target group or switch to EC2
   health checks, with exact CLI commands.

**End-to-end scenario:** see
[`skills/autoscaling-group-auditor/examples/end-to-end.md`](skills/autoscaling-group-auditor/examples/end-to-end.md)
for a production ASG walkthrough (ELB health check with no target group)
covering the infinite-replacement-loop concept, ordered classification, and
per-finding CLI remediation.

---

---

### 18. ecr-repository-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ecr-repository` — or route via `/aws:pipeline`.

**What it does:** Audits ECR private repositories for public-access exposure
via `repositoryPolicy` (`Principal: "*"` with pull/push actions and no strong
condition), image-scan configuration gaps (`scanOnPush: false` with unscanned
images), lifecycle-policy absence (no `lifecyclePolicyText`), tag-immutability
gaps (`MUTABLE` tags — supply-chain overwrite risk), and cross-account access.
Classifies each repository as PUBLIC, NO_SCAN, NO_LIFECYCLE, CONFIG_GAP, or OK
with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this ECR repository"
- "is my ECR repo public?"
- "check ECR repository policy"
- "is scan-on-push enabled?"
- "does this repo have a lifecycle policy?"
- "are there unscanned images?"
- "is tag immutability set?"
- "ECR cross-account access"

**Example session:**

You: "This ECR repo grants ecr:BatchGetImage to Principal '*' with no
condition. scanOnPush is false."

Skill:
1. Classifies the repositoryPolicy statement: WILDCARD_PRINCIPAL + PULL
   actions + no condition → PUBLIC (any AWS account holder can pull every
   image layer, exposing source code and embedded secrets).
2. Checks scanOnPush: false + images with imageScanStatus: null → NO_SCAN.
3. Emits VERDICT: PUBLIC (worst finding wins).
4. Remediation: remove the wildcard principal, enable scanOnPush, manually
   scan existing images, assume breach and audit CloudTrail for pull events.

**End-to-end example:** see
[`skills/ecr-repository-auditor/examples/end-to-end.md`](skills/ecr-repository-auditor/examples/end-to-end.md)
for a four-finding audit walkthrough (PUBLIC pull grant, NO_SCAN with
unscanned images, NO_LIFECYCLE, CONFIG_GAP mutable tags) covering severity
aggregation, image-layer exposure reasoning, and assume-breach remediation.

---

### 19. efs-filesystem-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-efs-filesystem`

**What it does:** Audits EFS filesystems for encryption-at-rest, filesystem
policy public principal exposure, encryption-in-transit enforcement
(`aws:SecureTransport`), lifecycle management policies, and access point
governance. Emits a deterministic verdict (UNENCRYPTED | PUBLIC_POLICY |
CONFIG_GAP | OK) per filesystem with enumerated findings and specific
remediation.

**When to invoke (trigger phrases):**

- "audit this EFS filesystem"
- "is my EFS filesystem public"
- "check EFS encryption"
- "EFS filesystem policy too permissive"
- "review EFS lifecycle policy"
- "EFS access points configured"
- "harden EFS filesystem"
- reviewing an EFS filesystem before production deployment

**Example prompt:**

```
You: "This EFS filesystem has Principal * with ClientRootAccess in the
     policy, no lifecycle policy, and no TLS enforcement. What's the risk?"
```

**Expected behavior:**

1. Classifies the filesystem as PUBLIC_POLICY (Principal "*" with Client*
   actions and no restrictive condition — Rule 2a).
2. Notes ClientRootAccess as total filesystem compromise (no root squashing).
3. Identifies lifecycle and TLS gaps as additional CONFIG_GAP findings.
4. Provides assume-breach remediation: restrict principals, add conditions,
   enforce TLS, add lifecycle policy, create access points.

**End-to-end scenario:** see
[`skills/efs-filesystem-auditor/examples/end-to-end.md`](skills/efs-filesystem-auditor/examples/end-to-end.md)
for a production ML-dataset filesystem walkthrough (public root access +
missing lifecycle + missing TLS) covering severity aggregation, the
ClientRootAccess danger concept, and the assume-breach remediation workflow.

---

### 20. backup-plan-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-backup-plan`

**What it does:** Audits AWS Backup plans for coverage gaps (empty or missing
resource selections), vault risks (missing vault lock, governance-mode lock
bypassable by root, AWS-managed encryption key), impossible lifecycle
configurations (cold storage transition at or after deletion, retention below
vault-lock floor), and compliance violations (backup frequency below daily,
retention below 30 days). Emits a deterministic verdict
(COVERAGE_GAP | VAULT_RISK | NONCOMPLIANT | CONFIG_GAP | OK) per plan with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this backup plan"
- "check backup coverage"
- "is my backup vault locked?"
- "backup lifecycle invalid"
- "cold storage transition"
- "vault lock governance vs compliance"
- "backup retention too short"
- "ransomware protection backup"
- reviewing a backup plan before production deployment

**Example prompt:**

```
You: "This backup plan has MoveToColdStorageAfterDays: 90 and
     DeleteAfterDays: 30. Is the lifecycle valid?"
```

**Expected behavior:**

1. Classifies the lifecycle as impossible — cold storage transition (90) is
   at or after deletion (30), so the cold tier is never used (Step 1a).
2. Emits VERDICT: CONFIG_GAP — the first matching step in the ordered
   classification.
3. Reports vault, coverage, and schedule dimensions as OK (they pass their
   respective steps but CONFIG_GAP takes priority).
4. Provides lifecycle-fix remediation: set cold=30, delete=90, with CLI.

**End-to-end scenario:** see
[`skills/backup-plan-auditor/examples/end-to-end.md`](skills/backup-plan-auditor/examples/end-to-end.md)
for a production EFS backup walkthrough covering the impossible-lifecycle
concept, ordered classification priority, and cross-region copy assessment.

---

### 21. dlm-lifecycle-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-dlm-lifecycle-policy`

**What it does:** Audits AWS Data Lifecycle Manager (DLM) EBS snapshot
lifecycle policies for coverage gaps and silent-failure modes. Checks for
disabled policies (State: DISABLED creates zero snapshots), empty tag/resource
targets (TargetTags: [] matches no volumes), invalid schedules (5-field cron
is rejected; DLM requires 6-field with year), missing/weak retention
(Count:1 = no recovery history; missing RetainRule = unbounded quota cliff),
absent cross-region copy (single-region backup = no DR), CopyTags metadata
loss, and per-volume snapshot quota risk (Count >= 1000). Emits a
deterministic verdict (NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK) per policy
or workload with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this DLM lifecycle policy"
- "why did my EBS snapshots stop?"
- "is my DLM policy enabled?"
- "check DLM retention and DR"
- "is DLM actually working?"
- "EBS backup coverage"
- "DLM silent failure"
- reviewing a DLM policy before production deployment

**Example prompt:**

```
You: "This DLM policy is ENABLED with a daily schedule and 14-snapshot
     retention, but there's no cross-region copy. What's the gap?"
```

**Expected behavior:**

1. Classifies the policy State (ENABLED), target coverage (valid TargetTags),
   schedule validity (valid Interval), and retention strength (14 snapshots
   = sensible).
2. Identifies the missing CrossRegionCopyTargets as a DR gap (Step 7).
3. Emits VERDICT: CONFIG_GAP — single-region backup provides no disaster
   recovery posture.
4. Provides remediation: add a CrossRegionCopyTarget with an explicit KMS
   CMK in the DR region (do NOT rely on the destination region's default
   encryption), then verify DR snapshots via `describe-snapshots`.

**End-to-end scenario:** see
[`skills/dlm-lifecycle-policy-auditor/examples/end-to-end.md`](skills/dlm-lifecycle-policy-auditor/examples/end-to-end.md)
for a six-scenario walkthrough covering NO_POLICY (account with zero
policies), MISCONFIGURED (disabled policy + empty TargetTags), CONFIG_GAP
(no DR + weak retention with CopyTags false), and OK (clean production
policy with 6-field cron, 30-day retention, and cross-region copy).

---

### 22. ebs-volume-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ebs-volume`

**What it does:** Audits EBS volumes and snapshots for unencrypted state
(compliance violation under PCI/HIPAA/SOC2), unattached cost-waste volumes,
legacy volume types (gp2/io1/standard with online upgrade paths), stale
snapshots accumulating storage cost (with Fast Snapshot Restore cost-
dominance check), and public snapshots exposing block-level data to every
AWS account. Emits a deterministic verdict
(UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK)
per resource with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this EBS volume"
- "is my EBS volume encrypted"
- "unattached EBS volumes"
- "gp2 to gp3 upgrade"
- "io1 to io2 upgrade"
- "stale EBS snapshots"
- "public snapshot exposure"
- "CreateVolumePermission public"
- "EBS cost optimization"
- "EBS compliance violation"
- reviewing an EBS volume or snapshot before production deployment or a
  compliance audit

**Example prompt:**

```
You: "This EBS volume is unencrypted, gp2, and attached with
     DeleteOnTermination: true. It hosts our checkout config. PCI audit
     next week — what's the verdict and remediation?"
```

**Expected behavior:**

1. Classifies the volume as UNENCRYPTED (HIGH) — Step 1, the worst
   non-CRITICAL verdict. Cites PCI-DSS Requirement 3.4 explicitly.
2. Notes the DeleteOnTermination: true as a CONFIG_GAP finding inside the
   verdict (does not change the verdict; not in the enum).
3. Identifies gp2 as LEGACY_TYPE (LOW) and the region's missing
   encryption-by-default as an account-level CONFIG_GAP.
4. Provides the correct 7-step encryption-migration flow (snapshot →
   copy-snapshot --encrypted → create-volume → attach → fix
   DeleteOnTermination → detach → delete). Does NOT recommend
   "enable encryption" — EBS encryption is immutable per resource.
5. Surfaces `enable-ebs-encryption-by-default` as the higher-leverage
   account-level remediation (do this FIRST to stop future bleeding).

**End-to-end scenario:** see
[`skills/ebs-volume-auditor/examples/end-to-end.md`](skills/ebs-volume-auditor/examples/end-to-end.md)
for a PCI-DSS audit walkthrough (unencrypted gp2 data volume with
DeleteOnTermination: true) covering severity aggregation, the
encryption-immutability remediation flow, account-level root-cause
escalation, and the assume-breach snapshot-lineage workflow.

---

### 23. cur-cost-usage-report-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cur-cost-usage-report` — or route via `/aws:pipeline`.

**What it does:** Audits AWS Cost and Usage Report (CUR) configurations for
FinOps data pipeline health. Checks whether CUR is configured at all (NO_CUR),
whether data is fresh (STALE — hourly manifest > 48h, daily > 72h), and for
configuration gaps (CONFIG_GAP — wrong report version, CSV/GZIP format
blocking Athena, missing ATHENA artifact, S3 versioning disabled, missing
Resources schema element, RefreshClosedReports false). Emits a deterministic
verdict (NO_CUR | STALE | CONFIG_GAP | OK) per report definition.

**When to invoke (trigger phrases):**

- "audit this Cost and Usage Report"
- "is my CUR healthy?"
- "check CUR Athena integration"
- "why is my CUR stale?"
- "CUR not delivering to S3"
- "Athena cost query empty"
- "CUR report version check"
- "is hourly refresh enabled"
- "FinOps data pipeline audit"
- reviewing CUR before a cost-optimization initiative

**Example prompt:**

```
You: "Our hourly CUR hasn't delivered in 9 days and Athena queries
     return empty. The format is CSV/GZIP. What's wrong?"
```

**Expected behavior:**

1. Classifies freshness: 9-day-old manifest for hourly cadence exceeds
   the 48h staleness threshold (Step 2a).
2. Emits VERDICT: STALE — delivery pipeline has stopped.
3. Enumerates all CONFIG_GAP findings: CSV/GZIP blocks Athena (Step 3b),
   no ATHENA artifact (Step 3c), versioning state.
4. Provides specific remediation: diagnose delivery stall, switch to
   Parquet, add ATHENA artifact, run crawler CFN template.

**End-to-end scenario:** see
[`skills/cur-cost-usage-report-auditor/examples/end-to-end.md`](skills/cur-cost-usage-report-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (stale delivery + CSV format + no Athena +
no versioning + RefreshClosedReports false) covering ordered classification,
staleness thresholds, and the per-dimension remediation workflow.

---

### 23. elbv2-load-balancer-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-elbv2-load-balancer`

**What it does:** Audits AWS ELBv2 load balancers (ALB/NLB) for insecure TLS
listener policies (TLS 1.0/1.1, weak ciphers, cleartext HTTP with no HTTPS
redirect), disabled access logs, permissive security groups (all-ports-open,
internal-LB-exposed-to-internet), idle load balancers (zero healthy targets),
disabled cross-zone load balancing (NLB only — ALB cross-zone is always on),
and missing deletion protection. Emits a deterministic categorical verdict
(INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK)
per load balancer with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this load balancer"
- "check ALB TLS policy"
- "is my NLB secure"
- "load balancer access logs disabled"
- "permissive security group ALB"
- "idle load balancer no targets"
- "cross-zone load balancing NLB"
- "deletion protection load balancer"
- "ELBSecurityPolicy TLS 1.0"
- "ELBSecurityPolicy-2016-08"
- reviewing an ALB or NLB before production deployment or a compliance audit

**Example prompt:**

```
You: "This ALB uses ELBSecurityPolicy-2016-08 on its HTTPS listener and
     access logs are disabled. PCI-DSS audit next week — what's the risk?"
```

**Expected behavior:**

1. Classifies the SslPolicy: ELBSecurityPolicy-2016-08 includes TLS 1.0/1.1
   — deprecated by PCI-DSS, vulnerable to protocol-downgrade attacks.
2. Emits VERDICT: INSECURE_LISTENER (Step 1 — worst finding wins).
3. Identifies the access-logs gap as an additional HIGH finding (Step 3).
4. Provides CLI remediation: modify-listener SslPolicy to
   ELBSecurityPolicy-TLS13-1-2-2021-06, enable access logs with
   modify-load-balancer-attributes.

**End-to-end scenario:** see
[`skills/elbv2-load-balancer-auditor/examples/end-to-end.md`](skills/elbv2-load-balancer-auditor/examples/end-to-end.md)
for a PCI-DSS audit walkthrough (TLS 1.0 default policy + disabled access
logs) covering verdict aggregation, the default-policy-is-insecure insight,
and the per-verdict CLI remediation workflow.

---

### 24. route53-record-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-route53-records` — or route via `/aws:pipeline`.

**What it does:** Audits Route 53 record sets for missing health checks on
routing-policy records (failover, weighted, latency, geolocation, multivalue),
dangling ALIAS targets pointing to deleted AWS resources (ELB, CloudFront, S3
website, API Gateway), DNSSEC signing gaps on public hosted zones, private-IP
exposure in public zones, and TTL inconsistency within routing groups. Emits a
deterministic verdict (NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK)
per record with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit these Route 53 records"
- "is my DNS failover configured correctly?"
- "dangling DNS record"
- "missing health check on failover"
- "DNSSEC not enabled"
- "public hosted zone exposure"
- "Route 53 TTL inconsistency"
- "subdomain takeover risk"
- reviewing Route 53 records before production deployment or traffic surge

**Example prompt:**

```
You: "Our failover PRIMARY for api.example.com has no health check.
     Is that a problem? The zone also doesn't have DNSSEC."
```

**Expected behavior:**

1. Classifies the failover PRIMARY as NO_HEALTH_CHECK/CRITICAL (Step 2a) —
   Route 53 can never detect primary failure; failover is functionally
   disabled.
2. Notes the DNSSEC gap as an additive HIGH finding (Step 3a) —
   cache-poisoning susceptibility.
3. Recognises that failover SECONDARY without health check is valid
   fail-open behaviour (not flagged as NO_HEALTH_CHECK).
4. Provides remediation: create-health-check, change-resource-record-sets
   UPSERT, enable-hosted-zone-dnssec + create-key-signing-key + publish DS
   record at registrar.

**End-to-end scenario:** see
[`skills/route53-record-auditor/examples/end-to-end.md`](skills/route53-record-auditor/examples/end-to-end.md)
for a pre-traffic-surge audit walkthrough (failover PRIMARY without health
check + dangling CloudFront ALIAS + DNSSEC gap) covering severity aggregation,
the failover-disabled insight, and the assume-takeover remediation workflow.

---

### 24. cloudfront-distribution-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cloudfront-distribution`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my CloudFront distribution"
```

**What it does:** Audits CloudFront distributions for insecure TLS viewer
minimum protocol versions (TLSv1.2_2021 threshold — the year suffix is the
cipher policy, not the TLS version), viewer protocol policy (allow-all),
custom origin protocol (http-only / match-viewer), S3 website endpoint
origins (forces public bucket), missing Origin Access Control on S3 origins
(OAC vs legacy OAI distinction), missing WAF Web ACL association, disabled
access logging, absent geographic restrictions, and empty default root
object. Emits a deterministic verdict
(INSECURE_TLS | NO_OAC | CONFIG_GAP | OK) per distribution.

**When to invoke (trigger phrases):**

- "audit this CloudFront distribution"
- "is my CloudFront TLS secure"
- "check CloudFront OAC"
- "is OAC configured on my S3 origin"
- "does my distribution have a WAF"
- "CloudFront logging disabled"
- "geo restriction CloudFront"
- "ViewerProtocolPolicy allow-all"
- "OriginProtocolPolicy http-only"
- "S3 website endpoint origin"
- "hardening CloudFront before production"

**Example prompt:**

```
You: "This distribution uses TLSv1.2_2019 minimum protocol, the S3 origin
     has no OAC, and logging is disabled. Marketing site launch is tomorrow
     — what's the verdict and remediation?"
```

**Expected behavior:**

1. Classifies as INSECURE_TLS — TLSv1.2_2019 still permits CBC-mode ciphers;
   TLSv1.2_2021 restricts to AEAD-only (Step 2).
2. Also flags NO_OAC — S3 origin with no OAC and no OAI means the bucket
   must be publicly readable (Step 5).
3. Cites the CONFIG_GAP items (no WAF, no logging) as additional findings.
4. Provides CLI remediation: update MinimumProtocolVersion, create OAC and
   attach to origin, update S3 bucket policy, enable logging.

**End-to-end scenario:** see
[`skills/cloudfront-distribution-auditor/examples/end-to-end.md`](skills/cloudfront-distribution-auditor/examples/end-to-end.md)
for a marketing-site launch audit (TLSv1.2_2019 + no OAC + no logging)
covering cipher-suite-difference reasoning, the OAI-vs-OAC migration
workflow, and per-verdict CLI remediation.

---

### 25. billing-account-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-billing-account`

**What it does:** Audits an AWS account's billing posture across five
dimensions — root account security (MFA enabled, zero access keys), IAM
user/group billing access delegation vs root-only, Cost Anomaly Detection
enablement, billing budgets/alerts coverage, and free-tier usage alerts.
Emits a deterministic verdict
(ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK) per account with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit my billing configuration"
- "check billing access"
- "is Cost Anomaly Detection enabled"
- "do I have billing budgets"
- "is root MFA enabled"
- "billing alerts configured"
- "free tier usage alerts"
- "who can access billing"
- "root account billing access"
- "root access keys present"
- "FinOps audit"
- reviewing an account's billing posture before a FinOps compliance review

**Example prompt:**

```
You: "This account has root MFA on, IAM billing access activated,
     Cost Explorer enabled, one CAD monitor, one budget at $5000, and
     free-tier alerts on. But I just found a root access key — what's
     the billing verdict?"
```

**Expected behavior:**

1. Classifies the account as ROOT_BILLING (CRITICAL) — Step 1, because
   root access keys bypass MFA for every billing API call. This is the
   single most dangerous billing configuration and trumps all other
   dimensions.
2. Notes that root MFA being enabled is OK but irrelevant for API attacks
   using the access key — MFA protects console sign-in only.
3. Acknowledges the good configuration on all other dimensions (IAM
   delegation active, CAD with subscription, budget with alert, free-tier
   alerts on) as OK findings.
4. Provides the correct remediation: sign in as root in the console to
   delete the key (root keys cannot be managed by IAM users via CLI),
   then audit CloudTrail for `userIdentity.type: "Root"` billing API
   calls during the exposure window.

**End-to-end scenario:** see
[`skills/billing-account-auditor/examples/end-to-end.md`](skills/billing-account-auditor/examples/end-to-end.md)
for a FinOps compliance audit walkthrough (root access keys on an
otherwise clean account) covering worst-finding aggregation, the
MFA-bypass reasoning, and the root-only key-deletion remediation flow.

---

### 23. networkmanager-core-network-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-networkmanager-core-network`

**What it does:** Audits AWS Network Manager (Cloud WAN) core networks
for detached attachments (active traffic disruption), permissive resource
policies (wildcard or cross-account principals), CIDR overlap across VPC
attachments (silent routing ambiguity), and configuration gaps (LATEST vs
LIVE policy mismatch, orphaned segment references). Emits a deterministic
verdict (DETACHED_ATTACHMENT | PERMISSIVE_POLICY | CIDR_OVERLAP |
CONFIG_GAP | OK) per core network with enumerated findings and specific
CLI remediation.

**When to invoke (trigger phrases):**

- "audit this core network"
- "check Cloud WAN attachment status"
- "CIDR overlap in core network"
- "segment isolation check"
- "core network resource policy"
- "LATEST vs LIVE policy"
- "detached VPC attachment"
- "core network audit"
- "Cloud WAN audit"
- reviewing a core network policy before production deployment or
  opening it to cross-account teams

**Example prompt:**

```
You: "This Cloud WAN core network has a prod VPC and a non-prod VPC
     attached. The prod VPC is 10.0.0.0/16 and the non-prod is
     10.0.1.0/24. Are they safe to open to the shared-services team?"
```

**Expected behavior:**

1. Detects the CIDR overlap (10.0.1.0/24 is inside 10.0.0.0/16) —
   CIDR_OVERLAP verdict. Explains that Cloud WAN silently accepts
   overlapping CIDRs with no creation-time validation.
2. Checks AttachmentStatus (not just State) for every attachment —
   AVAILABLE + ATTACHED passes; AVAILABLE + DETACHED triggers
   DETACHED_ATTACHMENT.
3. Evaluates the resource policy for wildcard or cross-account
   principals without conditions — flags as PERMISSIVE_POLICY.
4. Verifies LATEST policy generation equals LIVE — a mismatch is a
   CONFIG_GAP (changes staged but not deployed).
5. Aggregates to the worst verdict: DETACHED_ATTACHMENT > CIDR_OVERLAP
   > PERMISSIVE_POLICY > CONFIG_GAP > OK.

**End-to-end scenario:** see
[`skills/networkmanager-core-network-auditor/examples/end-to-end.md`](skills/networkmanager-core-network-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (CIDR overlap + cross-account resource
policy) covering severity aggregation, the State-vs-Status distinction,
multi-CIDR VPC advertisement, and CLI remediation.

---

### 26. cost-optimization-hub-recommendations-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cost-optimization-hub`

**What it does:** Audits AWS Cost Optimization Hub configuration for
recommendation enablement, member-account coverage in Organizations,
effort-level distribution, and stale high-value unactioned recommendations.
Emits a deterministic verdict
(DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK) per account
with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit cost optimization hub"
- "are cost optimization recommendations enabled"
- "check member account enrollment cost optimization"
- "effort level distribution recommendations"
- "stale high-value recommendations"
- "unactioned cost optimization recommendations"
- "savings estimation mode check"
- "FinOps audit cost optimization hub"

**Example prompt:**

```
You: "Cost Optimization Hub is enrolled but all recommendations are High
     effort and savingsEstimationMode is BEFORE_DISCOUNTS. What's the gap?"
```

**Expected behavior:**

1. Applies the ordered classification (enablement -> member coverage ->
   effort distribution -> config gaps -> OK).
2. Emits VERDICT: HIGH_EFFORT (Step 3 — no Low/Medium effort quick wins
   remain).
3. Identifies the BEFORE_DISCOUNTS savings estimation mode as an additional
   CONFIG_GAP finding (Step 4b).
4. Provides remediation: verify CloudWatch agent deployment, switch to
   AFTER_DISCOUNTS mode, prioritize remaining recommendations by ROI.

**End-to-end scenario:** see
[`skills/cost-optimization-hub-recommendations-auditor/examples/end-to-end.md`](skills/cost-optimization-hub-recommendations-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (stale high-value recs + BEFORE_DISCOUNTS
mode + partial member enrollment) covering multi-finding aggregation, the
savings-overstatement concept, and low-effort-first remediation ordering.

### 23. directconnect-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-directconnect-topology`

**What it does:** Audits AWS Direct Connect topology for hybrid-network
resilience and link-security posture — physical-layer redundancy (2+
connections at **diverse** DX locations, not the same POP — same-location
pairs are pseudo-diversity), MACSec (IEEE 802.1AE) enforcement on capable
dedicated hardware (distinguishing `must_encrypt` from silent-downgrade
`should_encrypt`), BGP MD5 auth on public VIFs (route-hijack defence for
advertised public prefixes), virtual-interface redundancy across diverse
connections via a Direct Connect Gateway (multi-region failover), and
LOA-CFA provisioning state for connections stuck in `requested`. Emits a
deterministic verdict
(SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK) per topology with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Direct Connect connection"
- "is my DX redundant"
- "MACSec check Direct Connect"
- "BGP auth public VIF"
- "LOA stuck pending"
- "diverse location Direct Connect"
- "single path failure risk DX"
- "route hijack public VIF"
- "LAG redundancy audit"
- "Direct Connect Gateway failover"
- "should_encrypt vs must_encrypt"
- reviewing a Direct Connect topology before production cutover or a
  compliance audit

**Example prompt:**

```
You: "We just brought up a second Direct Connect connection for
     redundancy. Both terminate at EqSE2. Production hybrid apps depend
     on this link — give me the verdict before we declare cutover."
```

**Expected behavior:**

1. Classifies the topology as SINGLE_CONNECTION (HIGH) — Step 1, the
   worst verdict. Both connections share location EqSE2, so a single
   facility event takes both down. Cites the location-diversity rule
   explicitly.
2. Notes the public VIF without BGP MD5 (CONFIG_GAP, MEDIUM) as a
   secondary finding — route-hijack vector for the advertised prefix.
3. Surfaces MACSec `must_encrypt` on both connections as an OK dimension
   (does not change the verdict; not the worst finding).
4. Provides the correct 4-step remediation: provision a third connection
   at a different DX location (with lead-time caveat: 2-6 weeks),
   re-create the public VIF with `--auth-key` (BGP auth is not
   modifiable in-place), migrate routes via AS-path prepending, and
   optionally add IPsec VPN overlay if procurement is blocked.

**End-to-end scenario:** see
[`skills/directconnect-auditor/examples/end-to-end.md`](skills/directconnect-auditor/examples/end-to-end.md)
for a pre-cutover audit walkthrough (two same-POP connections with a
BGP-auth-less public VIF) covering location-diversity reasoning, the
`bgpAuthKey` write-only gotcha, worst-finding aggregation, and the
destructive VIF re-creation workflow.

---

### 27. budgets-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-budgets`

**What it does:** Audits AWS Budgets for cost-overrun blind spots: accounts
with zero budgets (NO_BUDGET), budgets configured without notifications or
with empty subscriber lists (NO_ALERT — decorative budgets), SNS topic
policies that silently block delivery because they omit the
`budgets.amazonaws.com` publish principal, single-threshold or no-early-
warning alert sets, COST budgets with ACTUAL-only notifications and no
FORECASTED signal, breached or on-track-to-breach actual-vs-forecast spend
with no matching notification, and missing zero-spend guardrails for new or
sandbox accounts. Emits a deterministic verdict
(NO_BUDGET | NO_ALERT | CONFIG_GAP | OK) per account with enumerated findings
and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit my AWS budgets"
- "check budget alerts"
- "is my budget wired to SNS"
- "budget notification threshold"
- "zero-spend budget"
- "cost overrun alert"
- "budget forecast exceeded"
- "spend posture audit"
- "budget SNS policy"
- "decorative budget"
- "budget not alerting"
- "budget alerts not working"
- reviewing cost budgets before a billing review or production cutover

**Example prompt:**

```
You: "We configured a budget but the alerts never arrive. Audit our
     spend posture before the monthly billing review."
```

**Expected behavior:**

1. Classifies the account as CONFIG_GAP — a 100% ACTUAL notification is
   wired to an SNS topic whose policy grants the account root but NOT the
   `budgets.amazonaws.com` service principal (Step 3 — silent delivery
   failure).
2. Notes the single 100% threshold leaves no reaction time (Step 4) and the
   absence of any FORECASTED notification removes the only lead-time signal
   given 8-14h cost-data lag (Step 5).
3. Surfaces the on-track breach: ForecastedSpend > BudgetLimit with no
   FORECASTED notification to fire on it (Step 6).
4. Provides additive remediation: back up the topic policy first, add the
   budgets service principal statement, then add a FORECASTED + an early-
   warning notification, while confirming total notifications stay <= 11.

**End-to-end scenario:** see
[`skills/budgets-auditor/examples/end-to-end.md`](skills/budgets-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (silent SNS delivery failure + single-
threshold + no-forecast + on-track breach) covering the
service-principal-vs-root distinction, cost-data-lag reasoning, and the
additive remediation ordering.

---

### 28. ce-cost-anomaly-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ce-cost-anomaly`

**What it does:** Audits AWS Cost Explorer (CE) anomaly-detection
subscriptions, Savings Plan/RI coverage gaps, idle-resource detection
readiness, and report-subscription cadence. Checks for zero CAD monitors
or zero subscriptions (NO_ANOMALY_SUB — total cost-spike blind spot),
steady-state eligible compute spend (>$1k/mo) with RI coverage < 40% AND
SP coverage < 40% (LOW_RI_COVERAGE — on-demand leak), and configuration
quality gaps: an IMMEDIATE monitor paired with a WEEKLY subscription
(notification latency >> detection latency), the $100 default threshold
on a free-tier or low-spend account, DAILY-only monitors with no
IMMEDIATE on accounts > $5k/mo, no CUR v2 with resource IDs (idle-
resource detection impossible via CE), and narrow monitor scope with no
org/linked-account breadth. Emits a deterministic verdict
(NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK) per account with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit Cost Anomaly Detection"
- "check my anomaly subscription"
- "is CAD wired correctly"
- "RI coverage gap"
- "Savings Plan coverage"
- "anomaly threshold too high"
- "idle resource detection"
- "IMMEDIATE vs DAILY monitor"
- "cost spike alerting"
- "commitment gap"
- "on-demand leak"
- reviewing CE/CAD configuration before a billing review or quarterly
  FinOps assessment

**Example prompt:**

```
You: "Review our Cost Explorer and Cost Anomaly Detection setup before
     the quarterly billing review. We spend about $20k/month on
     steady-state EC2 and want to make sure we're not leaking on-demand
     spend or missing cost spikes."
```

**Expected behavior:**

1. Classifies the account as LOW_RI_COVERAGE — $18k/mo eligible EC2
   spend with 22% RI / 12% SP coverage (Step 2 — commitment strategy
   absent or undersized on a steady-state fleet).
2. Notes the IMMEDIATE monitor is paired with a WEEKLY subscription
   (Step 3a — the monitor detects in ~5 min but the subscription
   delivers a digest 7 days later; the operator sees the spike a week
   late).
3. Flags the $100 default threshold as miscalibrated for a $20k/mo
   account (Step 3b — recommended ~$1000-$2000, i.e. 5-10% of monthly
   spend).
4. Distinguishes coverage (USAGE offset by commitment — the leak to
   close) from utilization (COMMITMENT consumed — over-buy waste). The
   LOW_RI_COVERAGE verdict means "run a commitment analysis," not "buy
   RIs today."

**End-to-end scenario:** see
[`skills/ce-cost-anomaly-auditor/examples/end-to-end.md`](skills/ce-cost-anomaly-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (frequency mismatch + threshold
miscalibration + low coverage) covering the frequency-vs-detection-
cadence distinction, the coverage-vs-utilization distinction, and the
additive remediation ordering.

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
