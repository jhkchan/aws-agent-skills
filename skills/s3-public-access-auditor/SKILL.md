---
name: s3-public-access-auditor
description: 'Audits S3 bucket configurations (Block Public Access settings, ACLs, bucket policies, Access Points, and Object Ownership) to determine which buckets are publicly accessible and provides specific remediation guidance. Use when reviewing S3 bucket security, checking for public access exposure, validating BPA settings, auditing bucket ACLs/policies for compliance, or inventorying exposure across hundreds of buckets in an account. Triggers: S3, bucket, public access, BPA, Block Public Access, bucket policy, ACL, AllUsers, AuthenticatedUsers, Principal:*, s3:GetObject, s3:PutObject, Access Point, Multi-Region Access Point, MRAP, Object Ownership, BucketOwnerEnforced, Object Writer, sourceIp, aws:sourceVpce, public read, public write, s3 exposure, data leak, bucket security, compliance check, bulk bucket audit.'
license: Apache-2.0
compatibility: Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI calls needed for analysis — the skill reasons over provided config text. For live remediation, AWS CLI v2 with s3api/s3control/accesspoints access.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  verdict_shape: PUBLIC | SAFE | AMBIGUOUS
  version: 0.4.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, s3, cloudops, security, public-access, bpa, bucket-policy, acl, audit, compliance
  dependencies: aws-orchestrator
  keywords: aws, s3, cloudops, security, public-access, bpa, block-public-access, bucket-policy, acl, audit, compliance, data-leak
  when_to_use: Invoke when the user supplies S3 bucket config (BPA settings, ACL JSON, bucket-policy JSON, Access Point ARN/policy, Object Ownership value) and asks to classify public exposure for one or many buckets; when triaging a potential S3 data-leak alert (GuardDuty finding, MACIE finding, security-hub rule); when hardening an account by inventorying all buckets for BPA/ACL/policy posture; or when validating that intended-public buckets (static website / CloudFront origin) are not over-exposed. Do NOT invoke for non-S3 storage (EBS/EFS/FSx) or for object-level encryption/KMS questions unless they affect the public-access verdict.
---

# S3 Public-Access Auditor

An AWS CloudOps agent skill that analyzes S3 bucket configurations (Block Public
Access settings, ACLs, and bucket policy snippets) to determine which buckets
are publicly accessible, classify each bucket's exposure level, and provide
specific remediation guidance.

## Activation keywords

audit, public access, BPA, Block Public Access, bucket policy, ACL, AllUsers,
AuthenticatedUsers, Principal:"*", s3:GetObject, s3:PutObject, Access Point,
Multi-Region Access Point, MRAP, Object Ownership, BucketOwnerEnforced,
Object Writer, aws:sourceVpce, aws:sourceIp, public read, public write,
s3 exposure, data leak, bucket security, compliance check, bulk bucket audit.

## Invocation contract (hard requirement)

When this skill is invoked with bucket configuration input (BPA settings,
ACL JSON, bucket-policy JSON, or any S3 bucket descriptor), the agent MUST
respond with the four-line per-bucket block defined in §"Output format"
using the literal all-caps labels `BUCKET:`, `VERDICT:`, `REASON:`,
`REMEDIATION:`. Do NOT preface the block with prose, headings, or
disclaimers — emit the block as the first lines of the response. This
contract is what assertion-based evals and downstream parsers rely on;
deviating from the literal labels breaks automation silently.

## Reasoning framework (why the procedure is ordered this way)

S3 has FIVE independent access-control planes that are evaluated by AWS in a
fixed precedence — the order of the procedure below mirrors that precedence
so the first matching rule is the one AWS would actually enforce:

1. **Block Public Access (BPA)** — a hard gate, evaluated first. When all 4 BPA
   settings are `True`, AWS suppression happens at the authorization layer
   BEFORE ACLs, policies, or access-point policies are evaluated. A public ACL
   still appears in `get-bucket-acl` output but is silently ignored; a
   `Principal: "*"` policy still parses but is restricted to principals within
   the owner account. So BPA is *authoritative* — checking it first avoids
   false positives on buckets that look exposed but are not.

2. **Object Ownership** — `BucketOwnerEnforced` (the default since April 2022)
   disables ALL ACLs on the bucket and any ACL grants present are silently
   ignored. If this value is set, the ACL plane is moot and ACL inspection
   becomes a no-op — but the bucket policy and access-point policies still
   apply. See §"Object Ownership setting".

3. **Bucket policy** — evaluated next. A bucket policy is attached JSON; even
   with BPA off, an `Allow` with `Principal: "*"` and no restrictive condition
   is a direct public read/write path. This is the most common leak pattern.

4. **ACL** — legacy cross-account / public grants via the ACL API. With BPA
   off and Object Ownership permitting ACLs, an `AllUsers` READ grant is a
   public read path that the bucket policy does not override (ACLs and
   policies are evaluated independently — the effective permission is the
   union of both).

5. **Access Points (and Multi-Region Access Points, MRAP)** — each Access
   Point has its OWN policy that is UNIONED with the bucket policy for
   requests addressed through the AP ARN (`arn:aws:s3:<region>:<acct>:accesspoint/<name>/...`).
   A "SAFE" bucket can be fully exposed via a single permissive AP. See
   §"Access Points and MRAP".

6. **Condition strength** — only evaluated when a `Principal: "*"` statement
   (on bucket OR access-point policy) has a `Condition`. A restrictive
   condition narrows access, but conditions vary in strength (see
   §"Condition strength matrix" and the full reference at
   `references/condition-strength-matrix.md`).

The order matters because each layer can MASK or REVEAL the next. The judge
should classify by the first rule that matches, in this order.

## Classification logic (apply in order — first match wins)

1. **BPA fully enabled at bucket level** (all 4 settings:
   `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`,
   `RestrictPublicBuckets` = `True`). The bucket is **SAFE** regardless of
   ACLs or policies. Bucket-level BPA is authoritative for that bucket
   independent of account-level BPA — see §"Account-level vs bucket-level
   BPA interaction" for the truth table. Cite "Rule 1: BPA authoritative".

2. **PUBLIC via unrestricted wildcard policy.** BPA is not fully enabled AND
   any statement in the bucket policy OR any access-point policy for the
   bucket has ALL of:
   - `Effect: Allow`
   - `Principal` of `"*"`, `{"AWS": "*"}`, or any principal that resolves to
     all principals (including `"*"` nested under `Service` or `Federated`)
   - `Action` including at least one of: `s3:GetObject`, `s3:*`,
     `s3:Get*`, `s3:Put*`, `s3:List*`, `s3:DeleteObject*`,
     `s3:PutBucketPolicy`, `s3:PutBucketAcl`, `s3:PutObjectAcl`,
     `s3:GetObjectVersion`
   - The `Resource` covers the object namespace
     (`arn:aws:s3:::bucket/*` or `arn:aws:s3:<region>:<acct>:accesspoint/<name>/object/*`)
     or the bucket / AP namespace itself — both are exploitable; object
     namespace is read/write of objects, bucket/AP namespace is config
     manipulation
   - **No `Condition`** OR a condition containing only weak keys (see
     §"Condition strength matrix" — a weak-conditioned statement is
     treated as PUBLIC, not AMBIGUOUS)

   Cite "Rule 2: unrestricted wildcard Allow". **Severity escalation:**
   if the action set includes write-side actions
   (`s3:PutObject`, `s3:DeleteObject`, `s3:PutBucketPolicy`,
   `s3:PutBucketAcl`, `s3:PutObjectAcl`, `s3:*`), escalate severity to
   **CRITICAL** in the reason (write open bucket → ransomware /
   data-destruct attack surface). Read-only (`s3:GetObject` /
   `s3:Get*` / `s3:List*`) stays at **HIGH** (data exfiltration).
   **Cross-plane escalation:** if the wildcard Allow lives on an Access
   Point policy rather than the bucket policy, note "exposure via Access
   Point `<name>` — reachable through the AP ARN regardless of bucket
   policy". See §"Access Points and MRAP".

3. **PUBLIC via legacy ACL.** BPA is not fully enabled AND Object Ownership
   permits ACLs (see §"Object Ownership setting") AND any ACL grant
   targets `AllUsers` (`http://acs.amazonaws.com/groups/global/AllUsers`)
   OR `AuthenticatedUsers`
   (`http://acs.amazonaws.com/groups/global/AuthenticatedUsers`) —
   `AuthenticatedUsers` means "any AWS account holder", which is
   effectively public (anyone can create a free AWS account).
   `READ` → public read; `WRITE` → public write (CRITICAL).
   Cite "Rule 3: legacy ACL grant". If Object Ownership is
   `BucketOwnerEnforced`, ACLs are disabled and any ACL grant in the input
   is a no-op — DO NOT fire Rule 3; fall through to Rule 5 (or note the
   stale grant as informational).

4. **AMBIGUOUS (restricted wildcard policy).** BPA is not fully enabled AND
   a `Principal: "*"` Allow exists BUT the `Condition` contains at least
   one STRONG condition key (see matrix). The bucket is not directly
   public, but a policy edit or condition removal could expose it. Cite
   "Rule 4: condition-restricted wildcard — fragile posture".

5. **SAFE (BPA off, no public configs).** BPA is not fully enabled but
   no public ACLs, no public policy statements (bucket OR access-point),
   no website-config exposure (see §"Website-hosting check"). Cite
   "Rule 5: clean config, recommend BPA as defense-in-depth".

## Account-level vs bucket-level BPA interaction

BPA exists at two scopes and they are NOT inherited — each is independently
evaluated, and the EFFECTIVE BPA state for a bucket is the most-restrictive
combination of both scopes per-setting:

| Setting                  | Effective value when bucket=A, account=B |
|--------------------------|------------------------------------------|
| `BlockPublicAcls`        | True if EITHER scope is True              |
| `IgnorePublicAcls`       | True if EITHER scope is True              |
| `BlockPublicPolicy`      | True if EITHER scope is True              |
| `RestrictPublicBuckets`  | True if EITHER scope is True              |

In other words: each setting is a logical OR across scopes — enabling a
setting at EITHER scope is sufficient; the more-restrictive scope wins.
Moved to [references/advanced-patterns.md](references/advanced-patterns.md#bpa-scope-interaction-practical-implications) — the four account-vs-bucket BPA postures and what each means for classification.
Load that reference on demand before executing this section.

Always state which scope(s) are set in the verdict reason so the operator
knows where to apply the remediation. When auditing input that omits the
account-level state, ASSUME account-level BPA is OFF (worst-case) and
note the assumption explicitly — do not silently infer protection.

## Object Ownership setting (`s3:GetBucketOwnershipControls`)

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#object-ownership-setting-s3getbucketownershipcontrols) — ObjectWriter / BucketOwnerPreferred / BucketOwnerEnforced and Rule 3 gating.
Load that reference on demand before executing this section.

## Access Points and Multi-Region Access Points (MRAP)

Each S3 Access Point has its OWN policy and is addressable via a separate
ARN (`arn:aws:s3:<region>:<acct>:accesspoint/<name>`). Requests made via
the AP ARN are evaluated against the UNION of the bucket policy and the
AP policy — so a permissive AP policy exposes the bucket even when the
bucket policy is restrictive. Multi-Region Access Points (MRAP) add a
single global ARN routed across regions, and an MRAP policy evaluated the
same way.

Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#access-points-and-mrap-audit-steps-and-cli) — list/get AP policies per region, apply Rules 2/4 to AP policies, MRAP policy fetch.
Load that reference on demand before executing this section.

## Procedural enumeration (large-account bulk audit)

For accounts with hundreds or thousands of buckets, the audit must
enumerate safely before classifying. Use this procedure:

Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#procedural-enumeration-large-account-bulk-audit) — paginated bucket listing, account BPA capture, parallel 5-input capture, per-region AP enumeration.
Load that reference on demand before executing this section.

## Multi-statement and malformed input handling

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#multi-statement-and-malformed-input-handling) — statement iteration, Deny-condition pitfalls, NotAction/NotPrincipal, cross-policy union, malformed JSON, object ACLs.
Load that reference on demand before executing this section.

## Condition strength matrix (summary)

When evaluating a `Principal: "*"` Allow with a `Condition`, classify the
condition to choose between Rule 2 (PUBLIC) and Rule 4 (AMBIGUOUS). The
full table — including less-common keys (`aws:CalledViaFirst`,
`aws:MultiFactorAuthAge`, `s3:ExistingObjectTag`, `kms:ViaService`,
`aws:PrincipalOrgID`, `aws:PrincipalArn`, VPC-endpoint service
exceptions) and the `IfExists` semantics for each — lives in
`references/condition-strength-matrix.md`. Inline summary:

**STRONG condition keys → AMBIGUOUS (Rule 4):**
- `aws:sourceVpce` / `aws:SourceVpce` (VPC Endpoint ID, `StringEquals`) —
  request must come through the named endpoint; not forgeable by the
  caller.
- `aws:sourceVpc` / `aws:SourceVpc` (VPC ID, `StringEquals`) — request
  must originate in the named VPC.
- `aws:SourceAccount` / `aws:SourceOrgID` / `aws:PrincipalOrgID` with
  `StringEquals` — restricts to a specific AWS account or Organizations
  org.
- `aws:sourceIp` (`aws:SourceIp`, `IpAddress`) restricted to a true
  private CIDR (RFC1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  or a documented corporate range — see §"CIDR nuance table".

**WEAK condition keys → still PUBLIC (Rule 2):**
- `aws:Referer` (StringLike/StringEquals on Referer header) — trivially
  forgeable by any HTTP client; provides NO real access control.
- `aws:UserAgent` — same; forgeable client-side.
- `aws:sourceIp` with `0.0.0.0/0` (or omitted — equivalent to /0) —
  covers the entire internet; treat as no restriction.
- `aws:EpochTime` / `s3:authType` used alone — narrow the channel but
  not the principal.
- Any condition key wrapped in `IfExists` — weakens the assertion; treat
  per the underlying key but flag the `IfExists` semantics (see reference).

### CIDR nuance table for `aws:sourceIp`

Moved to [references/condition-strength-matrix.md](references/condition-strength-matrix.md#cidr-nuance-table-for-awssourceip-moved-from-skillmd) — verdict per CIDR incl. /0, RFC1918, CGNAT, TEST-NET, split-halves bypass.
Load that reference on demand before executing this section.

## Website-hosting check

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#website-hosting-check) — website+BPA=SAFE(broken), website+public ACL/policy=PUBLIC amplification.
Load that reference on demand before executing this section.

## Output format (per bucket) — MANDATORY literal labels

When invoked with bucket configuration input, your ENTIRE response MUST be
the per-bucket block below (one block per bucket). The four labels are
**case-sensitive all-caps keywords** — write them EXACTLY as shown. Do NOT
substitute `Verdict`, `Reason`, `**VERDICT**`, `### Verdict`, or any
markdown variant. Do NOT write a preamble ("Based on the configuration…"),
an "Audit Findings" heading, or a trailing "Detailed Analysis" section.
Start with `BUCKET:` and stop after the `REMEDIATION:` line. A short
clarifying paragraph MAY follow the block if needed, but the block itself
MUST be the first thing in the response and MUST contain all four labels.

```text
BUCKET: <name>
VERDICT: PUBLIC | SAFE | AMBIGUOUS
REASON: <1-2 sentences citing the specific config — include which rule number fired and the severity for PUBLIC>
REMEDIATION: <specific action, or "None required" if safe>
```

**Worked example (copy the shape exactly):**

```text
BUCKET: logs-archive-2024
VERDICT: PUBLIC
REASON: Rule 3 (legacy ACL grant) — AllUsers READ grant; HIGH severity (public read of log archive data).
REMEDIATION: Enable BPA (all 4 settings), remove the AllUsers ACL grant (set ACL to private).
```

For a multi-bucket audit, emit one block per bucket, separated by a blank
line, then an optional summary table. Each block MUST contain the four
mandatory labels (`BUCKET`, `VERDICT`, `REASON`, `REMEDIATION`) — even if
REMEDIATION is "None required".

## NEVER (anti-patterns)

- NEVER classify a bucket as PUBLIC when BPA is fully enabled at the
  bucket level (all 4 settings True). Bucket-level BPA is authoritative
  for that bucket regardless of account-level BPA state — even a
  `Principal: "*"` policy is restricted to in-account principals. A
  false-positive PUBLIC on a BPA-protected bucket causes unnecessary
  ticket churn and erodes trust in the auditor.

- NEVER classify a bucket as SAFE when BPA is off and a policy grants
  `s3:GetObject` (or any read/write action in the §"Rule 2" list) to
  `Principal: "*"` with no restrictive condition. This is the most
  common S3 data-leak pattern.

- NEVER assume a `private` ACL means the bucket is safe when BPA is
  off. The ACL and the bucket policy are independent — a public policy
  overrides a private ACL because AWS unions the two. Check BOTH.

- NEVER classify a `Principal: "*"` Allow with a strong restrictive
  condition (`aws:sourceVpce`, `aws:sourceVpc`, `aws:SourceAccount`)
  as PUBLIC. The condition narrows access to a known network or
  account — the correct verdict is AMBIGUOUS. PUBLIC means anyone on
  the internet.

- NEVER treat a `Principal: "*"` Allow with a WEAK condition
  (`aws:Referer`, `aws:UserAgent`) as AMBIGUOUS. These keys are
  forgeable client-side and provide no real restriction — classify as
  PUBLIC. This is the inverse mistake of the previous rule.

- NEVER recommend enabling only some BPA settings. Each setting blocks
  a different vector: `BlockPublicAcls` blocks new public ACLs but not
  policies; `BlockPublicPolicy` blocks new public policies but ignores
  legacy ACLs; `IgnorePublicAcls` neutralizes existing ACLs;
  `RestrictPublicBuckets` restricts the blast radius of public policies
  already attached. Half-enabled BPA is a false sense of security.

- NEVER ignore `AuthenticatedUsers`
  (`http://acs.amazonaws.com/groups/global/AuthenticatedUsers`). Any
  AWS account holder can read/write — anyone can create a free-tier
  account. Treat identically to `AllUsers` for severity purposes.

- NEVER ignore the `Principal: "*"` in a `NotAction` statement. An
  Allow with `Principal: "*"`, `NotAction: "s3:Delete*"`, and no
  condition grants every action EXCEPT Delete to the world. Easy to
  miss in manual review — the skill must flag it as PUBLIC.

- NEVER treat static website hosting as automatically public. The
  feature does not grant access; it requires an ACL or policy to do
  so. Classify by the underlying ACL/policy, then note whether
  website hosting amplifies the exposure.

- NEVER recommend deleting the bucket policy as the first remediation
  step without first capturing the policy content (e.g., `aws s3api
  get-bucket-policy --output json > backup.json`). Some policies are
  load-bearing for application access; a destructive remediation
  must be reversible.

- NEVER trust a `Deny` with `Principal: "*"` as a positive signal of
  hardening without verifying the Deny's `Condition`. A Deny with
  `aws:SecureTransport: false` enforces TLS but says nothing about
  public exposure. A Deny with `aws:MultiFactorAuthPresent=false` does
  not restrict the principal set. A Deny with no condition DOES block
  all access — read the full statement.

- NEVER classify a bucket as SAFE when it has a permissive Access Point
  or Multi-Region Access Point policy, even if the bucket policy is
  restrictive. Requests addressed through the AP ARN bypass the bucket
  policy for that surface. Always enumerate APs (`list-access-points`)
  and audit their policies.

- NEVER recommend enabling only one BPA setting. A common pitfall is
  enabling `BlockPublicAcls` alone and concluding the bucket is safe —
  `BlockPublicPolicy` may still be False, leaving an existing public
  policy fully active. Verify all 4 settings are True at the chosen
  scope before declaring protection.

- NEVER treat a partial-BPA bucket (e.g., 3 of 4 settings True) as
  fully BPA-protected. Per the §"Account-level vs bucket-level BPA
  interaction" truth table, each setting is independent; the missing
  setting leaves its specific vector open. Fall through to the
  policy/ACL rules and flag the partial-BPA gap explicitly.

- NEVER infer account-level BPA state from a bucket-level reading (or
  vice versa). The two scopes are NOT inherited. If the input only
  provides one scope, ASSUME the other is OFF (worst case) and flag
  the assumption — silently inferring protection is the canonical
  cause of false-SAFE classifications.

- NEVER rely on `aws:sourceIp` with `0.0.0.0/0` (or a paired
  `0.0.0.0/1` + `128.0.0.0/1`) as a real restriction. The condition
  matches every IPv4 address; classify as PUBLIC (Rule 2). Same for
  any IP-list condition containing even a single `/0` entry — AWS
  ORs the list, so one open entry widens access.

- NEVER fire Rule 3 (legacy ACL) when Object Ownership is
  `BucketOwnerEnforced`. ACLs are disabled at the API layer on these
  buckets — any ACL grant in `get-bucket-acl` output is a cosmetic
  leftover. Note the stale grant but do not classify as PUBLIC via ACL.

- NEVER treat the bucket policy in isolation when Access Points are
  in scope. The effective permission for AP-addressed requests is the
  union of bucket policy + AP policy; a restrictive bucket policy
  does NOT restrict AP-addressed requests.

- NEVER deviate from the four-line output block. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` / `Conclusion:` (or any
  prose variant) for the literal `VERDICT:` label silently breaks
  downstream parsers and assertion-based evals. Same for `REASON:`
  and `REMEDIATION:`. The labels are uppercase, end with a colon,
  and appear on their own line. Even when REMEDIATION is "None
  required", the label MUST be present.

- NEVER preface the verdict block with a preamble like "Based on the
  configuration…" or an "### Audit Findings" heading. The first
  non-blank line of the response MUST be `BUCKET: <name>`. A short
  clarifying section may FOLLOW the block, but the block itself must
  lead the response.

## Pre-flight safety checks (run before any remediation CLI)

- Confirm the bucket exists in the target account/region:
  `aws s3api head-bucket --bucket <name>` — fail closed (skip
  remediation) if it returns an error.
- Capture current state for rollback:
  `aws s3api get-bucket-policy --bucket <name> --output json > /tmp/<name>-policy-backup-$(date +%s).json`
  and
  `aws s3api get-bucket-acl --bucket <name> --output json > /tmp/<name>-acl-backup-$(date +%s).json`
  BEFORE any modification.
- Prefer additive changes (enable BPA) over destructive changes (delete
  policy). Enabling BPA is reversible by setting all 4 back to False;
  deleting a policy may lose application access intent.
- For write-open buckets (PUBLIC with `s3:PutObject`/`s3:DeleteObject`),
  treat as incident-response — enable BPA IMMEDIATELY before capturing
  full forensic state, because every second of write-open exposure is
  data destruction risk. Capture state AFTER containing.

## Remediation guidance

Moved to [references/bpa-settings-and-cli-commands.md](references/bpa-settings-and-cli-commands.md#remediation-guidance-per-verdict-moved-from-skillmd) — action plans for PUBLIC read/write/ACL, AMBIGUOUS, SAFE postures.
Load that reference on demand before executing this section.

## Remediation for Access-Point-exposed buckets

Moved to [references/bpa-settings-and-cli-commands.md](references/bpa-settings-and-cli-commands.md#remediation-for-access-point-exposed-buckets-moved-from-skillmd) — AP policy tightening, account BPA, CloudFront OAC fronting, MRAP propagation.
Load that reference on demand before executing this section.

## Remediation for partial-BPA buckets

Moved to [references/bpa-settings-and-cli-commands.md](references/bpa-settings-and-cli-commands.md#remediation-for-partial-bpa-buckets-moved-from-skillmd) — same-scope completion, IgnorePublicAcls inertness note, BucketOwnerEnforced fix.
Load that reference on demand before executing this section.

## Adjacent postures worth flagging (not part of the verdict)

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#adjacent-postures-worth-flagging-not-part-of-the-verdict) — KMS key-policy backdoor, Object Lambda APs, VPC endpoint policies.
Load that reference on demand before executing this section.

## Recent AWS features (2024-2026)

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026) — directory buckets, Access Grants, S3 Tables, Express One Zone, versioning defaults.
Load that reference on demand before executing this section.

## References

- `references/bpa-settings-and-cli-commands.md` — full BPA enablement
  CLI commands (with pre-flight backup), account-level vs bucket-level
  detail, CloudFront OAC migration snippet, copy-pasteable remediation.
- `references/condition-strength-matrix.md` — exhaustive table of
  strong vs weak condition keys (including rare keys:
  `aws:CalledViaFirst`, `aws:MultiFactorAuthAge`, `s3:authType`,
  `s3:ExistingObjectTag`, `kms:ViaService`), `IfExists` semantics, and
  worked examples for each.

## Section taxonomy (CloudOps auditor pattern)

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#section-taxonomy-cloudops-auditor-pattern) — the 17-section canonical order this skill follows.
Load that reference on demand before executing this section.


## References (load on demand)

- [references/bpa-settings-and-cli-commands.md](references/bpa-settings-and-cli-commands.md) — full BPA enablement/verification CLI, account vs bucket scope, ACL/policy removal, CloudFront OAC, per-verdict remediation guidance.
- [references/condition-strength-matrix.md](references/condition-strength-matrix.md) — exhaustive strong/weak condition-key table, IfExists semantics, CIDR nuance table, worked examples.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — bulk-audit enumeration commands and Access-Point/MRAP audit CLI.
- [references/advanced-patterns.md](references/advanced-patterns.md) — BPA scope implications, Object Ownership, edge-case handling, website check, adjacent postures, recent AWS features.
## Domain

AWS CloudOps / S3 Security & Compliance.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **S3 Security Best Practices** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
- **S3 API Reference** — https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
- **S3 CLI Reference (s3api)** — https://docs.aws.amazon.com/cli/latest/reference/s3api/index.html
- **S3 CLI Reference (high-level s3)** — https://docs.aws.amazon.com/cli/latest/reference/s3/index.html
- **Block Public Access** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- **S3 Access Grants** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-grants.html
