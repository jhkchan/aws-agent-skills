# Error Handling — Security Hub Control-Compliance Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 0 — malformed JSON ERROR emit block

```text
CONTROL: <unknown>
VERDICT: WARNING
REASON: Input JSON is malformed — cannot extract Compliance block. Triage manually.
SEVERITY: MEDIUM
REMEDIATION: Re-fetch the finding via GetFindings by finding ID. If the source
integration is sending malformed ASFF, open a support case.
```

### Step 0 — missing Compliance block emit

```text
CONTROL: <ProductFields.ControlId or GeneratorId>
VERDICT: NOT_APPLICABLE
REASON: Finding has no Compliance block — this is an integration or custom
product finding, not a Security Hub control evaluation.
SEVERITY: <from Severity.Label, or INFORMATIONAL if missing>
REMEDIATION: Route to the appropriate detector skill (GuardDuty, Inspector).
```

## API and CLI constraints

**Security Hub API limits:**
- `GetFindings` returns **max 100 findings per page**. Use `--next-token` for
  pagination. Large accounts require multiple paginated calls.
- `BatchUpdateFindings` accepts **max 100 finding identifiers per call**.
  The `Note` field has a **4 KB limit** — truncate verbose justifications.
- `GetEnabledStandards` and `BatchGetStandardsControlAssociations` have lower
  throughput limits — cache the standards list.
- Updates via `BatchUpdateFindings` are **eventually consistent** (~30 seconds
  to reflect in `GetFindings`). Do not re-query immediately after an update
  expecting instant visibility.

**Throttling and retry:**
- Security Hub API calls are subject to **rate limiting** (token bucket).
  On `ThrottlingException`, use exponential backoff (`--retry-mode adaptive`
  on the CLI, or boto3 `botocore.config.Config` with `retry_mode='adaptive'`).
- Config rule evaluations also throttle under heavy load.

**CLI failure recovery:**
- `batch-update-findings` fails with `InvalidInputException` → finding
  identifier is malformed or the finding no longer exists. Skip and continue.
- Remediation fails with `AccessDenied` → verify caller has service-level
  permission AND no SCP or permissions boundary is blocking. Security Hub
  findings do not check SCPs — a finding can report a state the caller cannot
  modify.
- `aws s3api put-public-access-block` fails with `NoSuchBucket` → bucket was
  deleted between finding and remediation. Mark finding ARCHIVED.

