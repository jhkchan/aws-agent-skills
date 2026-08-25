# S3 Condition Strength Matrix — full reference

Detailed companion to the inline summary in `SKILL.md`. Use this when
classifying a `Principal: "*"` Allow with a `Condition` — the keys below
determine whether the statement is Rule 2 (PUBLIC) or Rule 4 (AMBIGUOUS).

## STRONG keys → AMBIGUOUS (Rule 4)

These keys bind to a network, account, or organizational identity that
the caller cannot forge.

| Key                                   | Operator           | Strength notes |
|---------------------------------------|--------------------|----------------|
| `aws:sourceVpce` / `aws:SourceVpce`   | `StringEquals`     | VPC Endpoint ID (e.g., `vpce-1a2b3c4d5e6f7g8h9`). Request must traverse the named endpoint; not forgeable by the caller. |
| `aws:sourceVpc` / `aws:SourceVpc`     | `StringEquals`     | VPC ID. Same non-forgeable property. |
| `aws:SourceAccount`                   | `StringEquals`     | Restricts to a specific AWS account ID. Strong against anonymous callers but does not protect against compromised IAM in that account. |
| `aws:PrincipalOrgID`                  | `StringEquals`     | Restricts to an AWS Organizations org ID (`o-xxxxxxxxxx`). |
| `aws:SourceOrgID`                     | `StringEquals`     | Same as PrincipalOrgID for resource-based policies with service principals. |
| `aws:sourceIp` (RFC1918 private CIDR) | `IpAddress`        | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` — reachable only from inside a VPC or corporate VPN. Real boundary. |
| `aws:sourceIp` (small public CIDR)    | `IpAddress`        | `/24` or smaller corporate egress range — narrow enough to be a boundary. Audit whether it is still the corp egress. |
| `s3:DataAccess` (AuthAccount)         | `StringEquals`     | S3 Access Grants managed permissions — not a `Principal: "*"` pattern but worth recognizing. |
| `kms:ViaService`                      | `StringEquals`     | KMS-level coupling (e.g., `kms:ViaService: s3.us-east-1.amazonaws.com`) — relevant when the bucket is KMS-encrypted and the KMS key policy is the real gate. |

## WEAK keys → still PUBLIC (Rule 2)

These keys are caller-controlled or so broad they are equivalent to no
restriction.

| Key                                   | Operator           | Weakness notes |
|---------------------------------------|--------------------|----------------|
| `aws:Referer`                         | `StringLike` / `StringEquals` | The Referer HTTP header is set by the client; any HTTP client can forge it. Provides NO real access control. Common in legacy CloudFront → S3 setups. |
| `aws:UserAgent`                       | `StringLike` / `StringEquals` | User-Agent is client-controlled. Forgeable. |
| `aws:sourceIp` (`0.0.0.0/0`)          | `IpAddress`        | Matches all IPv4 — equivalent to no condition. |
| `aws:sourceIp` (`::/0`)               | `IpAddress`        | Matches all IPv6 — same. |
| `aws:sourceIp` paired `/1` list       | `IpAddress`        | `0.0.0.0/1` + `128.0.0.0/1` together cover all IPv4; common bypass. |
| `aws:sourceIp` list with any `/0`     | `IpAddress`        | AWS ORs the list; one open entry widens access. |
| `aws:EpochTime` / `aws:CurrentTime`   | numeric / date     | Restricts WHEN, not WHO. Useful for temporal gating but not for access control alone. |
| `s3:authType`                         | `StringEquals`     | `REST-HEADER` vs `REST-QUERY-STRING` — narrows the channel but not the principal. |
| `s3:locationConstraint`               | `StringEquals`     | Restricts target region for bucket creation — irrelevant for read access. |
| `s3:prefix` / `s3:max-keys`           | `StringEquals`     | Affects ListObjects behavior, not authorization. |
| `aws:MultiFactorAuthPresent`          | `Bool`             | Only meaningful for IAM-user callers; anonymous (`*`) requests bypass MFA checks entirely. Do NOT treat as a restriction on `Principal: "*"`. |
| `aws:MultiFactorAuthAge`              | `NumericLessThan`  | Same caveat — irrelevant for anonymous callers. |

## Conditional (depends on configuration)

| Key                      | When AMBIGUOUS                                   | When PUBLIC                                            |
|--------------------------|--------------------------------------------------|--------------------------------------------------------|
| `aws:sourceIp`           | RFC1918, CGNAT (`100.64.0.0/10`), TEST-NET, narrow corp range | `0.0.0.0/0`, `::/0`, paired `/1` bypass, list with `/0` |
| `aws:TokenIssueTime`     | Combined with role-session restrictions          | Alone, irrelevant to principal set                     |
| `aws:PrincipalArn`       | When used in a `StringEquals` on a specific ARN within an org | When combined with a wildcard match like `arn:aws:iam::*:role/*` |
| `aws:PrincipalTag/*`     | When the tag set is restricted to internal roles | When the tag matches a generic value like `department: *` |
| `s3:ExistingObjectTag/*` | Narrow tag value                                 | Wildcard tag value                                     |

## `IfExists` semantics

`...IfExists` operators change the evaluation: if the key is NOT present
in the request context, the condition evaluates to TRUE (the statement
matches). This means:

- `aws:sourceVpce` with `StringEqualsIfExists` → AMBIGUOUS (the named
  VPCe still gates; absent key passes through, but only anonymous
  non-VPCe requests skip the check — moderate weakness).
- `aws:MultiFactorAuthPresent` with `BoolIfExists` → for anonymous
  requests the key is absent so the statement matches; not a
  restriction on `Principal: "*"`.
- `aws:Referer` with `StringLikeIfExists` → weak (forgeable header
  when present, skipped when absent).

When in doubt, classify `IfExists` as one notch weaker than the same
key without `IfExists`.

## Worked example: mixed strength list

```json
"Condition": {
  "IpAddress": { "aws:SourceIp": ["10.0.0.0/8", "203.0.113.5/32", "0.0.0.0/0"] }
}
```

The list contains both strong and weak entries. AWS evaluates
`IpAddress` as an OR over the list — any matching CIDR satisfies the
condition. The `0.0.0.0/0` entry matches every IPv4, so the condition
is effectively vacuous. **Verdict: PUBLIC (Rule 2)** — the weak entry
dominates.

## Cross-references

- AWS S3 BPA reference: https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- AWS global condition keys: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
- S3-specific condition keys: https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html

## CIDR nuance table for aws:sourceIp (moved from SKILL.md)

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

