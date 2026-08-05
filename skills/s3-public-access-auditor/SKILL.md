---
name: s3-public-access-auditor
description: "Audits S3 bucket configurations (Block Public Access settings, ACLs, bucket policies, Access Points, and Object Ownership) to determine which buckets are publicly accessible and provides specific remediation guidance. Use when reviewing S3 bucket security, checking for public access exposure, validating BPA settings, auditing bucket ACLs/policies for compliance, or inventorying exposure across hundreds of buckets in an account. Triggers: S3, bucket, public access, BPA, Block Public Access, bucket policy, ACL, AllUsers, AuthenticatedUsers, Principal:*, s3:GetObject, s3:PutObject, Access Point, Multi-Region Access Point, MRAP, Object Ownership, BucketOwnerEnforced, Object Writer, sourceIp, aws:sourceVpce, public read, public write, s3 exposure, data leak, bucket security, compliance check, bulk bucket audit."
version: 0.4.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: "Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI calls needed for analysis — the skill reasons over provided config text. For live remediation, AWS CLI v2 with s3api/s3control/accesspoints access."
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
  version: 0.4.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [aws, s3, cloudops, security, public-access, bpa, bucket-policy, acl, access-points, object-ownership, audit, compliance]
  dependencies:
    - aws-orchestrator
  keywords:
    - s3
    - public access
    - bpa
    - block public access
    - bucket policy
    - acl
    - access point
    - multi-region access point
    - object ownership
    - audit
    - compliance
  when_to_use: "Invoke when the user supplies S3 bucket config (BPA settings, ACL JSON, bucket-policy JSON, Access Point ARN/policy, Object Ownership value) and asks to classify public exposure for one or many buckets; when triaging a potential S3 data-leak alert (GuardDuty finding, MACIE finding, security-hub rule); when hardening an account by inventorying all buckets for BPA/ACL/policy posture; or when validating that intended-public buckets (static website / CloudFront origin) are not over-exposed. Do NOT invoke for non-S3 storage (EBS/EFS/FSx) or for object-level encryption/KMS questions unless they affect the public-access verdict."
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

Always state which scope(s) are set in the verdict reason so the operator
knows where to apply the remediation. When auditing input that omits the
account-level state, ASSUME account-level BPA is OFF (worst-case) and
note the assumption explicitly — do not silently infer protection.

## Object Ownership setting (`s3:GetBucketOwnershipControls`)

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

## Access Points and Multi-Region Access Points (MRAP)

Each S3 Access Point has its OWN policy and is addressable via a separate
ARN (`arn:aws:s3:<region>:<acct>:accesspoint/<name>`). Requests made via
the AP ARN are evaluated against the UNION of the bucket policy and the
AP policy — so a permissive AP policy exposes the bucket even when the
bucket policy is restrictive. Multi-Region Access Points (MRAP) add a
single global ARN routed across regions, and an MRAP policy evaluated the
same way.

Audit steps (when Access Point info is in the input):

1. Enumerate APs: `aws s3control list-access-points --account-id <acct>`
   (one per region; iterate regions).
2. For each AP, fetch its policy:
   `aws s3control get-access-point-policy --account-id <acct> --name <ap>`
3. Apply Rules 2 and 4 against the AP policy (in addition to the bucket
   policy). Resource matching for AP policies uses the AP ARN, not the
   bucket ARN — be permissive about Resource matching since AP policies
   commonly use `arn:aws:s3:::accesspoint/<name>/*` shorthand.
4. If ANY AP policy exposes the bucket, the verdict is **PUBLIC** with
   reason "Rule 2 (Access Point) — wildcard Allow on AP `<name>`; the
   bucket policy is bypassed for requests through the AP ARN".
5. If an AP policy uses `s3:DataAccess` or `s3:ExternalService` (bucket
  -managed permissions via S3 Access Grants), note it but do not classify
   as public — those are managed internally.

**MRAP-specific note:** an MRAP policy can route requests to ANY region's
bucket copy. A permissive MRAP policy exposes all underlying buckets in
all regions. Audit via `aws s3control get-multi-region-access-point-policy
--account-id <acct> --name <mrap>`.

## Procedural enumeration (large-account bulk audit)

For accounts with hundreds or thousands of buckets, the audit must
enumerate safely before classifying. Use this procedure:

1. **List all buckets (paginated):**
   ```bash
   # AWS CLI v2 auto-paginates; for very large accounts use --page-size
   aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n'
   ```
   For >10,000 buckets, set `--page-size 1000` and consider scripting with
   `boto3.Paginator` to avoid CLI truncation.

2. **Capture the account-level BPA ONCE** (it applies to all buckets):
   ```bash
   aws s3control get-public-access-block --account-id <acct>
   ```

3. **Per bucket, capture the 5 needed inputs in parallel:**
   ```bash
   for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n'); do
     aws s3api get-bucket-location              --bucket "$b" 2>/dev/null
     aws s3api get-public-access-block          --bucket "$b" 2>/dev/null
     aws s3api get-bucket-acl                   --bucket "$b" 2>/dev/null
     aws s3api get-bucket-policy                --bucket "$b" 2>/dev/null
     aws s3api get-bucket-ownership-controls    --bucket "$b" 2>/dev/null
   done > "/tmp/s3-audit-$(date +%s).jsonl"
   ```
   Wrap each in `2>/dev/null` and check exit codes — `NoSuchBucket`,
   `NoSuchPublicAccessBlockConfiguration`, and `AccessDenied` are common
   and should be classified as "data incomplete — manual review" rather
   than silently treated as SAFE.

4. **For Access-Point-aware audits,** enumerate APs per region:
   ```bash
   for r in us-east-1 us-west-2 eu-west-1 ap-southeast-2; do
     aws s3control list-access-points --profile default --region "$r" --account-id <acct>
   done
   ```
   Note: AP listing is region-scoped — a bucket in `us-east-1` may have
   APs in OTHER regions routing to it; iterate all enabled regions.

5. **Output one verdict per bucket** in the standard format below, and a
   summary table sorted by severity (CRITICAL → HIGH → AMBIGUOUS → SAFE).

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

| CIDR in condition                       | Verdict               | Reasoning                                                        |
|-----------------------------------------|-----------------------|------------------------------------------------------------------|
| `0.0.0.0/0` (or missing)                | PUBLIC (Rule 2)       | Covers entire IPv4 internet; equivalent to no restriction.       |
| `::/0`                                  | PUBLIC (Rule 2)       | Same for IPv6.                                                   |
| `10.0.0.0/8` / `172.16.0.0/12` / `192.168.0.0/16` | AMBIGUOUS (Rule 4) | RFC1918 private; only reachable from inside a VPC or corp VPN.   |
| `100.64.0.0/10` (CGNAT)                 | AMBIGUOUS (Rule 4)    | Shared carrier-grade NAT; large ISP surface but not "internet".  |
| `203.0.113.0/24` (TEST-NET-3)           | AMBIGUOUS (Rule 4)    | Documentation range; treat as private.                           |
| A specific public /24 or smaller        | AMBIGUOUS (Rule 4)    | Corporate egress range; narrow enough to be a real boundary.     |
| `0.0.0.0/1` + `128.0.0.0/1` pair        | PUBLIC (Rule 2)       | Common bypass — two halves that together cover all IPv4.         |
| Multi-value list including any `/0`     | PUBLIC (Rule 2)       | AWS unions the list; one `/0` entry nullifies the restriction.   |

For `aws:SourceIp` lists containing MIXED strong + weak entries, the
weak entry dominates (PUBLIC) — AWS evaluates the condition as an OR
within the list, so any permissive CIDR widens access.

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

## Remediation for Access-Point-exposed buckets

1. Tighten or replace the offending AP policy. Prefer replacing the
   wildcard Allow with a `Principal` listing the specific IAM role(s)
   or service(s) that need access through the AP.
2. Enable BPA at the account level (covers bucket and AP surfaces).
3. If public access through the AP is genuinely required (e.g., a public
   download endpoint), front the AP with CloudFront OAC rather than
   exposing it via `Principal: "*"`.
4. For MRAP, audit the policy at the global ARN — it propagates to all
   underlying regional buckets.

## Remediation for partial-BPA buckets

1. Set the remaining BPA setting(s) to True at the SAME scope as the
   existing ones (or escalate to account-level for consistency).
2. If the gap is `IgnorePublicAcls`, note that existing public ACLs
   only become inert AFTER this is set — the grant is still present in
   `get-bucket-acl` output and will be re-honored if `IgnorePublicAcls`
   is later unset. Recommend setting `Object Ownership = BucketOwnerEnforced`
   for a permanent fix (ACLs disabled at the API layer).

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

## Domain

AWS CloudOps / S3 Security & Compliance.
