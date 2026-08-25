# Macie Data Discovery Operator — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — three Macie realities (extended detail)

- **Macie must be enabled BEFORE any classification job or finding can
  exist.** A baseline model jumps to `create-classification-job` without
  checking whether Macie is enabled. The pre-flight gate catches this —
  Macie enablement is a prerequisite, not an afterthought.

- **Classification jobs are NOT real-time.** A scheduled job runs on a
  CRON-like schedule (every 1-30 days). A one-time job runs once. For
  continuous scanning of all S3, use automated ML-based discovery (the
  latest feature) — but even that has a scan frequency, not instant
  detection.

- **Findings are only as good as the data identifiers configured.**
  Managed identifiers detect common PII (SSN, credit card, email,
  phone). Custom identifiers use regex for organization-specific
  patterns (employee IDs, internal token formats). Without custom
  identifiers, Macie misses organization-specific sensitive data.

## Expert heuristic: finding severity and detection coverage

Macie findings come in two categories. A baseline model conflates them;
this heuristic distinguishes them for triage and remediation:

| Finding type | Category | What it detects | Severity range |
|---|---|---|---|
| `policy:IAMUser/S3` | Policy finding | Publicly accessible or shared S3 buckets (ACL, bucket policy) | Low, Medium, High |
| `sensitiveData:S3Object/Custom` | Sensitive data finding | Custom data identifier matched (regex) | High (configurable) |
| `sensitiveData:S3Object/Multiple` | Sensitive data finding | Multiple managed identifiers matched in one object | High |
| `sensitiveData:S3Object/<Identifier>` | Sensitive data finding | Specific managed identifier (e.g., `USA_SOCIAL_SECURITY_NUMBER`) | Medium-High |

**Coverage rule:** managed identifiers detect ~150+ PII types across
regions (US SSN, UK NINO, credit card, email, phone, passport, API
keys). If the organization has custom data formats (employee IDs,
internal tokens, proprietary formats), custom identifiers are REQUIRED
for full coverage — managed identifiers will miss them.

**Severity triage:** `policy:IAMUser/S3` findings (public bucket) are
typically higher urgency than `sensitiveData:S3Object/Email` (email in
a private bucket). But `sensitiveData:S3Object/Credit_Card` in a public
bucket is critical. Cross-reference the finding type with the bucket
exposure (public vs private) for prioritization.

## Expert heuristic: detection coverage gap analysis

A baseline model says "Macie finds PII." This heuristic explains what
Macie misses:

```text
Detection Coverage
   ├─ Managed identifiers (~150+ PII types)
   │    ├─ US SSN, passport, driver's license — YES
   │    ├─ Credit card, bank account, SWIFT — YES
   │    ├─ AWS access keys, API tokens — YES
   │    ├─ Email, phone, address — YES
   │    └─ Organization-specific formats (employee IDs, internal tokens)?
   │         └─ NO — requires custom data identifiers (regex)
   │
   ├─ Custom identifiers (regex + keywords)
   │    ├─ Effectiveness depends on regex precision
   │    ├─ Keyword proximity scope reduces false positives
   │    └─ Must be maintained as data formats evolve
   │
   └─ Automated ML-based discovery
        ├─ ML-adaptive — samples content, selects identifiers
        ├─ Still NOT instant (queued scan frequency)
        └─ Does NOT replace custom identifiers for proprietary formats
```

**Practical implication:** for full coverage, combine managed
identifiers (for common PII), custom identifiers (for proprietary
formats), and automated discovery (for ML-adaptive scanning). Relying on
any single method leaves gaps.

## Recent AWS features (2024-2026)

- **Macie automated data discovery (ML-based, 2024-2025):** ML-driven
  continuous scanning of all S3 without manual classification jobs.
  Adapts identifier selection based on bucket content sampling.
  Provisioning tip: enable for comprehensive coverage, keep targeted
  jobs for specific high-risk buckets.
- **Cross-account Macie findings aggregation (2024-2025):** Org-level
  delegated admin aggregates findings from all member accounts. Use
  `list-findings` in the admin account to query across all members.
  Verify `relationshipStatus=Enabled` for all members.
- **Macie + Step Functions remediation (2024-2025):** Multi-step
  remediation workflows triggered by EventBridge. Parse finding details,
  quarantine objects, restrict ACLs, notify teams. More sophisticated
  than single-Lambda remediation.
- **Enhanced managed data identifiers (2024):** Expanded coverage for
  credentials (API keys, private keys), financial data (IBAN, SWIFT),
  and region-specific PII (new country passport formats).
- **Sensitive data discovery for S3 Object Lambda (2024):** Macie scans
  S3 Object Lambda access points for sensitive data transformed on the
  fly.
- **Automated discovery scope controls (2025-2026):** Scope automated
  discovery to specific accounts or buckets within the org. Reduces cost
  for large orgs where not all S3 needs scanning.

