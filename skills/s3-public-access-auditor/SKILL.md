---
name: s3-public-access-auditor
description: "Audits S3 bucket configurations (Block Public Access settings, ACLs, and bucket policies) to determine which buckets are publicly accessible and provides specific remediation guidance. Use when reviewing S3 bucket security, checking for public access exposure, validating BPA settings, or auditing bucket ACLs and policies for compliance. Triggers: S3, bucket, public access, BPA, Block Public Access, bucket policy, ACL, AllUsers, AuthenticatedUsers, Principal:*, s3:GetObject, s3:PutObject, public read, public write, s3 exposure, data leak, bucket security, compliance check."
version: 0.3.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: "Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI calls needed for analysis — the skill reasons over provided config text. For live remediation, AWS CLI v2 with s3api/s3control access."
keywords:
  - aws
  - s3
  - cloudops
  - security
  - public-access
  - bpa
  - block-public-access
  - bucket-policy
  - acl
  - audit
  - compliance
  - data-leak
tags: [aws, s3, cloudops, security, public-access, bpa, bucket-policy, acl, audit, compliance]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  verdict_shape: "PUBLIC | SAFE | AMBIGUOUS"
  version: 0.3.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [aws, s3, cloudops, security, public-access, bpa, bucket-policy, acl, audit, compliance]
  dependencies:
    - aws-orchestrator
  keywords:
    - s3
    - public access
    - bpa
    - block public access
    - bucket policy
    - acl
    - audit
    - compliance
  when_to_use: "Reviewing S3 bucket security, checking for public access exposure, validating BPA settings, auditing bucket ACLs and policies for compliance, or investigating potential data-leak vectors."
---

# S3 Public-Access Auditor

An AWS CloudOps agent skill that analyzes S3 bucket configurations (Block Public
Access settings, ACLs, and bucket policy snippets) to determine which buckets
are publicly accessible, classify each bucket's exposure level, and provide
specific remediation guidance.

## Activation keywords

audit, public access, BPA, Block Public Access, bucket policy, ACL, AllUsers,
AuthenticatedUsers,Principal:"*", s3:GetObject, s3:PutObject, public read,
public write, s3 exposure, data leak, bucket security, compliance check.

## Reasoning framework (why the procedure is ordered this way)

S3 has THREE independent access-control planes that are evaluated by AWS in a
fixed precedence — the order of the procedure below mirrors that precedence
so the first matching rule is the one AWS would actually enforce:

1. **Block Public Access (BPA)** — a hard gate, evaluated first. When all 4 BPA
   settings are `True`, AWS suppression happens at the authorization layer
   BEFORE ACLs or policies are evaluated. A public ACL still appears in
   `get-bucket-acl` output but is silently ignored; a `Principal: "*"` policy
   still parses but is restricted to principals within the owner account. So
   BPA is *authoritative* — checking it first avoids false positives on
   buckets that look exposed but are not.

2. **Bucket policy** — evaluated next. A bucket policy is attached JSON; even
   with BPA off, an `Allow` with `Principal: "*"` and no restrictive condition
   is a direct public read/write path. This is the most common leak pattern.

3. **ACL** — legacy cross-account / public grants via the ACL API. With BPA
   off, an `AllUsers` READ grant is a public read path that the bucket policy
   does not override (ACLs and policies are evaluated independently — the
   effective permission is the union of both).

4. **Condition strength** — only evaluated when a `Principal: "*"` statement
   has a `Condition`. A restrictive condition narrows access, but conditions
   vary in strength (see §"Condition strength matrix" below).

The order matters because each layer can MASK or REVEAL the next. The judge
should classify by the first rule that matches, in this order.

## Classification logic (apply in order — first match wins)

1. **BPA fully enabled at bucket level** (all 4 settings:
   `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`,
   `RestrictPublicBuckets` = `True`). The bucket is **SAFE** regardless of
   ACLs or policies. Bucket-level BPA is authoritative for that bucket
   independent of account-level BPA. Cite "Rule 1: BPA authoritative".

2. **PUBLIC via unrestricted wildcard policy.** BPA is not fully enabled AND
   any statement in the bucket policy has ALL of:
   - `Effect: Allow`
   - `Principal` of `"*"`, `{"AWS": "*"}`, or any principal that resolves to
     all principals (including `"*"` nested under `Service` or `Federated`)
   - `Action` including at least one of: `s3:GetObject`, `s3:*`,
     `s3:Get*`, `s3:Put*`, `s3:List*`, `s3:DeleteObject*`,
     `s3:PutBucketPolicy`, `s3:PutBucketAcl`, `s3:PutObjectAcl`,
     `s3:GetObjectVersion`
   - The `Resource` covers the object namespace
     (`arn:aws:s3:::bucket/*`) or the bucket itself
     (`arn:aws:s3:::bucket`) — both are exploitable; object namespace
     is read/write of objects, bucket namespace is config manipulation
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

3. **PUBLIC via legacy ACL.** BPA is not fully enabled AND any ACL grant
   targets `AllUsers` (`http://acs.amazonaws.com/groups/global/AllUsers`)
   OR `AuthenticatedUsers`
   (`http://acs.amazonaws.com/groups/global/AuthenticatedUsers`) —
   `AuthenticatedUsers` means "any AWS account holder", which is
   effectively public (anyone can create a free AWS account).
   `READ` → public read; `WRITE` → public write (CRITICAL).
   Cite "Rule 3: legacy ACL grant".

4. **AMBIGUOUS (restricted wildcard policy).** BPA is not fully enabled AND
   a `Principal: "*"` Allow exists BUT the `Condition` contains at least
   one STRONG condition key (see matrix). The bucket is not directly
   public, but a policy edit or condition removal could expose it. Cite
   "Rule 4: condition-restricted wildcard — fragile posture".

5. **SAFE (BPA off, no public configs).** BPA is not fully enabled but
   no public ACLs, no public policy statements, no website-config
   exposure (see §"Website-hosting check"). Cite "Rule 5: clean config,
   recommend BPA as defense-in-depth".

## Multi-statement and malformed input handling

- **Iterate every statement** in a multi-statement policy. A bucket is
  PUBLIC if ANY statement matches Rule 2 or Rule 3. A bucket is AMBIGUOUS
  if ANY statement matches Rule 4 and no statement matches Rules 2/3.
  Deny statements (`Effect: Deny`) override Allows and should be noted but
  do not downgrade an existing PUBLIC finding unless the Deny blocks the
  same principal/action/resource tuple (rare in practice — most Denies
  target different conditions like `aws:SecureTransport: false`).

- **`NotAction` / `NotPrincipal` / `NotResource`.** These inverted fields
  expand the matched set. `Principal: "*"` with `NotAction: "s3:Delete*"`
  means "every action except Delete is allowed publicly" — treat as
  PUBLIC (Rule 2). Flag explicitly because the inverse field is easy to
  miss in manual review.

- **Malformed JSON.** If the bucket policy fails to parse or is missing
  required fields (`Effect`, `Principal`, `Action` or `NotAction`,
  `Resource` or `NotResource`), output:
  `VERDICT: AMBIGUOUS` with reason "bucket policy unparseable — manual
  review required". Do NOT silently classify as SAFE.

- **Object-level ACLs.** The skill audits bucket-level ACLs by default.
  If object-level ACLs are reported in the input and any object ACL
  grants `AllUsers` or `AuthenticatedUsers`, treat as PUBLIC via
  object ACL and cite "Rule 3 (object-level)".

## Condition strength matrix

When evaluating a `Principal: "*"` Allow with a `Condition`, classify the
condition to choose between Rule 2 (PUBLIC) and Rule 4 (AMBIGUOUS):

**STRONG condition keys → AMBIGUOUS (Rule 4):**
- `aws:sourceVpce` (VPC Endpoint ID) — request must come through the named
  endpoint; not forgeable by the caller.
- `aws:sourceVpc` (VPC ID) — request must originate in the named VPC.
- `aws:SourceVpce` / `aws:SourceVpc` in a `StringEquals` — same as above.
- `kms:ViaService` — KMS-level coupling (does not affect S3 directly but
  appears in KMS+S3 hybrid policies).
- `aws:SourceAccount` / `aws:SourceOrgID` with `StringEquals` — restricts
  to a specific AWS account or Organizations org.

**WEAK condition keys → still PUBLIC (Rule 2):**
- `aws:Referer` (StringLike/StringEquals on Referer header) — trivially
  forgeable by any HTTP client; provides NO real access control.
- `aws:UserAgent` — same; forgeable client-side.
- `aws:sourceIp` (`aws:SourceIp`) with a public CIDR — restricts to a
  network range, which is meaningful for static IPs but is bypassable
  when the caller controls egress; classify as AMBIGUOUS for non-public
  CIDRs (RFC1918) but PUBLIC if the CIDR itself is `0.0.0.0/0` or
  broader than the intended audience.
- Any condition key wrapped in `IfExists` — weakens the assertion; treat
  per the underlying key but flag the `IfExists` semantics.

## Website-hosting check

A bucket configured for static website hosting (`aws s3 website`) does
NOT by itself grant public read — but it requires the bucket to be
public-readable to serve content, so it pairs with either a public ACL
or a public policy. Treat the combination:

- Website hosting ENABLED + BPA fully on → **SAFE** (BPA blocks the
  public access the website feature would normally require; the website
  will return 403 — flag as broken, but not as a security exposure).
- Website hosting ENABLED + BPA off + public read ACL or policy →
  **PUBLIC** (Rule 2 or 3 fires first; note "website hosting amplifies
  exposure — indexed by search engines and discoverable via the
  `s3-website-<region>.amazonaws.com` endpoint").

## Output format (per bucket)

```text
BUCKET: <name>
VERDICT: PUBLIC | SAFE | AMBIGUOUS
REASON: <1-2 sentences citing the specific config — include which rule number fired and the severity for PUBLIC>
REMEDIATION: <specific action, or "None required" if safe>
```

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
  public exposure. A Deny with no condition DOES block all access —
  read the full statement.

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

For **PUBLIC** buckets (policy-based, read-only):

1. Enable BPA at both account and bucket level (all 4 settings True).
2. Remove or restrict the public-read policy statement.
3. If public CDN access is intended, use CloudFront with Origin Access
   Control (OAC — the current AWS recommendation; OAI is legacy but
   still supported) instead of a bucket-level public policy.

For **PUBLIC** buckets (policy-based, write-capable — CRITICAL):

1. Enable BPA at both account and bucket level IMMEDIATELY (this is
   the fastest containment — it blocks the public policy in seconds).
2. After containment, audit CloudTrail (`s3:PutObject`,
   `s3:DeleteObject` events on the bucket) for the window of exposure
   to identify unauthorized writes. Use CloudTrail Lake event data
   stores or Athena queries on the `CloudTrail` S3 bucket.
3. Rotate any keys or credentials that may have been deposited in the
   bucket.

For **PUBLIC** buckets (ACL-based):

1. Enable BPA at both account and bucket level (all 4 settings True).
2. Remove the AllUsers / AuthenticatedUsers ACL grant:
   `aws s3api put-bucket-acl --bucket <name> --acl private`.

For **AMBIGUOUS** buckets:

1. Enable BPA (all 4 settings) as defense-in-depth — the condition
   protects now but a policy edit could remove it.
2. Replace the Allow-based restricted policy with an explicit Deny
   (deny all except the trusted VPCe/VPC/account) — Deny statements
   cannot be accidentally widened by adding a new Allow.
3. If the condition is `aws:sourceIp` on a public CIDR, treat the
   bucket as effectively PUBLIC (the CIDR restriction is not a real
   boundary if it covers the open internet or a broad ISP range) and
   apply the PUBLIC remediation path.
4. Flag for security team review to validate the condition is still
   correct and that the named VPCe/VPC still exists.

For **SAFE** buckets (BPA off, no public configs):

1. No remediation required for current exposure.
2. Recommend enabling BPA (all 4 settings) as defense-in-depth.
3. If website hosting is enabled and BPA is off, recommend either
   enabling BPA + CloudFront OAC for public content, or disabling
   website hosting if the bucket should be private.

For **SAFE** buckets (BPA fully enabled):

1. No remediation required. BPA is authoritative.

## References

See `references/bpa-settings-and-cli-commands.md` for the full BPA
enablement CLI commands (with pre-flight backup), account-level vs
bucket-level BPA details, CloudFront OAC migration snippet, and
copy-pasteable remediation commands.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections
in this canonical order:

1. **Frontmatter** — name, description, version.
2. **Activation keywords** — discoverability terms.
3. **Reasoning framework** — the *why* behind the procedure order.
4. **Classification logic** — the ordered decision tree.
5. **Edge-case handling** — multi-statement, malformed, edge-case
   branches.
6. **Condition strength matrix** (or equivalent depth reference).
7. **Output format** — the fixed per-resource report shape.
8. **NEVER** — anti-patterns with explicit *why* each is wrong.
9. **Pre-flight safety checks** — non-destructive operation guards.
10. **Remediation guidance** — per-verdict action plan.
11. **References** — pointer to deeper references.

## Domain

AWS CloudOps / S3 Security & Compliance.
