# Advanced Patterns — S3 Public-Access Auditor

Deep-dive material moved from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## BPA scope interaction: practical implications

Practical implications:

- **Account-level BPA fully on + bucket-level BPA unset/False** → the
  bucket IS fully protected (account-level covers it). This is the most
  common production posture: enable once at the account level and all
  buckets (including future ones) inherit protection.
- **Bucket-level BPA fully on + account-level BPA off** → the bucket IS
  protected. This is the case the classification logic treats as SAFE
  (Rule 1).
- **Bucket-level BPA partially on (e.g., only `BlockPublicAcls=True`) +
  account-level BPA off** → the bucket is PARTIALLY protected: existing
  public policies still grant access if `BlockPublicPolicy` is False. Do
  NOT call this "fully BPA-protected" — fall through to Rules 2-5 based
  on the actual policy/ACL state, and flag the partial-BPA gap.
- **Both scopes off** → BPA provides zero protection; classify by
  policy/ACL/AP state.

## Object Ownership setting (s3:GetBucketOwnershipControls)

The bucket's `ObjectOwnership` value governs whether ACLs are honored at
all. Three values exist; only the first two honor ACLs:

- **`ObjectWriter`** (legacy default pre-2022) and **`BucketOwnerPreferred`**
  (writing objects, the bucket owner becomes the owner) — ACLs are HONORED.
  If BPA is off and a public ACL exists, Rule 3 fires.
- **`BucketOwnerEnforced`** (default for new buckets since April 2022) —
  ACLs are DISABLED. All ACL grants in `get-bucket-acl` output are
  cosmetic no-ops. Bucket-owner enforcement also breaks legacy
  cross-account workflows that relied on ACLs (e.g., CloudTrail logs from
  a logging account). Do not fire Rule 3 on these buckets; note any
  stale ACL grants as informational ("ACL grant present but ignored —
  ObjectOwnership=BucketOwnerEnforced").

When the input does not specify `ObjectOwnership`, assume `ObjectWriter`
(the worst-case that honors ACLs) for classification, but flag the
assumption in the reason and recommend the operator confirm via
`aws s3api get-bucket-ownership-controls --bucket <name>`.

## Multi-statement and malformed input handling

- **Iterate every statement** in a multi-statement policy. A bucket is
  PUBLIC if ANY statement matches Rule 2 or Rule 3. A bucket is AMBIGUOUS
  if ANY statement matches Rule 4 and no statement matches Rules 2/3.
  Deny statements (`Effect: Deny`) override Allows and should be noted but
  do not downgrade an existing PUBLIC finding unless the Deny blocks the
  same principal/action/resource tuple (rare in practice — most Denies
  target different conditions like `aws:SecureTransport: false`).

- **Deny-statement inspection (subtle pitfall).** A `Deny` with
  `Principal: "*"` is NOT automatically a hardening signal — read the
  `Condition`. Common patterns:
  - `Deny s3:* where aws:SecureTransport=false` → enforces TLS only;
    does NOT block public read over HTTPS. Bucket is still PUBLIC if an
    Allow matches.
  - `Deny s3:* where aws:SourceIp != <range>` (using `StringNotEquals` /
    `IpAddress` negation) → blocks everything EXCEPT the listed CIDRs.
    This IS a real restrictive Deny and can downgrade PUBLIC to
    AMBIGUOUS — but check whether the CIDR list is `0.0.0.0/0` (which
    negates to "block nothing").
  - `Deny s3:* where aws:SourceVpce != <vpce>` (StringNotEquals) →
    blocks everything outside the named VPCe. This is the strongest
    restrictive pattern; downgrade AMBIGUOUS to "defensible" (still
    not Rule 1 SAFE — BPA is the only hard gate).
  - `Deny s3:* where aws:MultiFactorAuthPresent=false` → enforces MFA
    for IAM users but does NOT restrict the principal set; a `Principal:
    "*"` Allow is still exploitable by any anonymous caller because
    MFA conditions only apply to authenticated IAM principals.

- **`NotAction` / `NotPrincipal` / `NotResource`.** These inverted fields
  expand the matched set. `Principal: "*"` with `NotAction: "s3:Delete*"`
  means "every action except Delete is allowed publicly" — treat as
  PUBLIC (Rule 2). Flag explicitly because the inverse field is easy to
  miss in manual review.

- **Cross-policy union (bucket + Access Point).** A bucket may have a
  restrictive bucket policy but a permissive Access Point policy.
  Iterate both policy documents independently and report the worst-case
  verdict. A restrictive bucket policy does NOT downgrade a PUBLIC AP
  verdict — the AP ARN bypasses the bucket policy for AP-addressed
  requests.

- **Malformed JSON.** If the bucket policy fails to parse or is missing
  required fields (`Effect`, `Principal`, `Action` or `NotAction`,
  `Resource` or `NotResource`), output:
  `VERDICT: AMBIGUOUS` with reason "bucket policy unparseable — manual
  review required". Do NOT silently classify as SAFE.

- **Object-level ACLs.** The skill audits bucket-level ACLs by default.
  If object-level ACLs are reported in the input and any object ACL
  grants `AllUsers` or `AuthenticatedUsers`, treat as PUBLIC via
  object ACL and cite "Rule 3 (object-level)". Note: Object Ownership
  = `BucketOwnerEnforced` disables object ACLs too — re-apply the same
  ownership check before firing this rule.

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

## Adjacent postures worth flagging (not part of the verdict)

These do not change the PUBLIC/SAFE/AMBIGUOUS verdict but should be
noted in the verdict reason when observed:

- **KMS key policy as a backdoor.** A bucket may be classified SAFE at
  the S3 layer but the underlying KMS CMK has a wildcard or cross-account
  `Resource`-based key policy granting `kms:Decrypt` / `kms:GenerateDataKey`
  to outsiders. The bucket objects are still effectively readable via
  the key — recommend auditing `aws kms get-key-policy --key-id <key>`
  for the bucket's encryption key. This is out of scope for the S3
  verdict but is the most common path to a "SAFE" misclassification in
  practice.
- **S3 Object Lambda Access Points.** An Object Lambda AP transforms
  objects on read but inherits the underlying AP's policy posture.
  Treat the same as a regular AP for exposure purposes.
- **VPC endpoint policies.** A permissive VPC endpoint policy
  (`Allow *` on `s3:*`) does not expose a private bucket to the
  internet, but it widens in-account blast radius if the VPC is shared
  (transit-gateway peering, shared subnets). Note as defense-in-depth.

## Recent AWS features (2024-2026)

- **S3 directory buckets for analytics (2024-2025):** S3 directory buckets (`AWS::S3Express::DirectoryBucket`) provide single-digit-millisecond latency for analytics workloads. These have a different bucket-level BPA model — auditors should verify that directory bucket access controls are equivalent to standard buckets and that directory bucket policies do not grant public access.
- **S3 Access Grants (2024):** S3 Access Grants provides identity-based access management for S3 data, simplifying permission management at scale. Auditors should verify that Access Grants instances are configured with scoped locations and that the IAM role for Access Grants is least-privilege.
- **S3 Tables (2024-2025):** S3 Tables provide managed tabular storage (Apache Iceberg) directly in S3. Auditors should verify that table bucket policies follow the same BPA and encryption standards as standard buckets.
- **New storage classes — S3 Express One Zone (2024):** `EXPRESS_ONE_ZONE` storage class for low-latency workloads. No audit-surface change for access control, but auditors should note that Express One Zone is single-AZ — verify that data durability requirements accommodate single-zone storage.
- **S3 Object Versioning default behavior changes (2024-2025):** AWS is moving toward enabling S3 Object Versioning by default on new buckets. Auditors should verify that versioning is intentionally enabled or disabled (not silently defaulted) and that lifecycle rules handle versioned objects.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections
in this canonical order:

1. **Frontmatter** — name, description, version, when-to-use.
2. **Activation keywords** — discoverability terms.
3. **Reasoning framework** — the *why* behind the procedure order.
4. **Classification logic** — the ordered decision tree.
5. **BPA scope interaction** — account-level vs bucket-level truth table.
6. **Object Ownership setting** — ACL-honoring state.
7. **Access Points and MRAP** — the cross-plane exposure surface.
8. **Bulk enumeration** — large-account audit procedure.
9. **Edge-case handling** — multi-statement, Deny nuances, malformed input.
10. **Condition strength matrix (summary)** — inline summary, full
    reference in `references/condition-strength-matrix.md`.
11. **CIDR nuance table** — worked `aws:sourceIp` examples.
12. **Website-hosting check** — amplification context.
13. **Output format** — the fixed per-resource report shape.
14. **NEVER** — anti-patterns with explicit *why* each is wrong.
15. **Pre-flight safety checks** — non-destructive operation guards.
16. **Remediation guidance** — per-verdict action plan, plus AP/partial-BPA
    and adjacent-posture flags (KMS backdoor, Object Lambda, VPCe policy).
17. **References** — pointer to deeper references.

