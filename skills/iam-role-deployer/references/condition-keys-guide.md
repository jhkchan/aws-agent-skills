# IAM Condition Keys Reference Guide

Supplementary reference for the IAM Role Deployer skill. Use when
selecting condition keys for trust policies and permission policies.

## Condition key categories

### Network-scoping keys (strong to weak)

| Key | Set by | Forgeable? | Strength | Use case |
|---|---|---|---|---|
| `aws:SourceVpce` | VPC endpoint infrastructure | No | Strongest | Bind to specific VPC endpoint |
| `aws:SourceVpc` | VPC infrastructure | No | Strong | Bind to specific VPC |
| `aws:SourceArn` | The calling AWS service | No | Strong | Bind Lambda role to specific function |
| `aws:SourceAccount` | The calling AWS service | No | Strong | Bind service role to owning account |
| `aws:SourceIp` | Caller's IP | Yes (NAT/proxy/VPN) | Weak | Corporate network restriction (defense-in-depth only) |
| `aws:UserAgent` | Caller's HTTP client | Yes (trivial) | Very weak | Never rely on for security |

**Rule:** Use `aws:SourceVpce` or `aws:SourceVpc` for network-scoped
conditions. These are set by AWS infrastructure and cannot be forged by
the caller. `aws:SourceIp` is bypassable via NAT Gateway, proxy, or VPN.

### aws:SourceArn and aws:SourceAccount

Set by the AWS service that is assuming the role on behalf of a resource.
The caller (the resource itself) cannot forge these values.

```json
"Condition": {
  "StringEquals": {
    "aws:SourceAccount": "111111111111"
  },
  "ArnLike": {
    "aws:SourceArn": "arn:aws:lambda:us-east-1:111111111111:function:my-app-*"
  }
}
```

- `aws:SourceAccount` is always a 12-digit account ID.
- `aws:SourceArn` is the full ARN of the calling resource. Use `ArnLike`
  with wildcards for families, `StringEquals` for exact match.
- ALWAYS include BOTH `SourceAccount` and `SourceArn` in service role
  trust policies. `SourceArn` alone can match cross-account if the ARN
  pattern is broad. `SourceAccount` adds the account-level guard.

### aws:SourceVpc and aws:SourceVpce

Set by VPC endpoint infrastructure when a request comes through a VPC
endpoint. The caller cannot forge these.

```json
"Condition": {
  "StringEquals": {
    "aws:SourceVpc": "vpc-aaaabbbbcccc"
  }
}
```

```json
"Condition": {
  "StringEquals": {
    "aws:SourceVpce": "vpce-aaaabbbbccccdddd"
  }
}
```

- `aws:SourceVpc` matches the VPC ID where the request originated.
- `aws:SourceVpce` matches the specific VPC endpoint ID. Tighter than
  SourceVpc.
- These keys are ONLY present when the request goes through a VPC
  endpoint. Direct internet requests do NOT have these keys. Use
  `IfExists` if you want to allow both endpoint and non-endpoint access.

### aws:SourceIp

```json
"Condition": {
  "IpAddress": {
    "aws:SourceIp": ["10.0.0.0/8", "203.0.113.0/24"]
  }
}
```

- Set from the caller's source IP as seen by IAM.
- **Bypassable:** A caller behind a NAT Gateway, proxy, VPN, or corporate
  firewall can change their apparent source IP.
- Use for defense-in-depth, NEVER as the sole network-scoping mechanism.
- `aws:SourceIp` does NOT match IPv6 — use `aws:SourceVpc` for IPv6.

### MFA keys (human-accessible roles only)

| Key | Type | Purpose |
|---|---|---|
| `aws:MultiFactorAuthPresent` | Bool | Is MFA presented? |
| `aws:MultiFactorAuthAge` | Numeric | Seconds since MFA authentication |

```json
"Condition": {
  "Bool": {"aws:MultiFactorAuthPresent": "true"},
  "NumericLessThan": {"aws:MultiFactorAuthAge": "3600"}
}
```

**Critical rules:**
- `Bool` qualifier is MANDATORY. Without it, the condition silently fails
  for ALL requests (including those with MFA).
- `aws:MultiFactorAuthAge` forces re-authentication after N seconds. 3600
  (1 hour) is standard; 900 (15 min) for break-glass.
- These keys do NOT exist for service principals. Services do not present
  MFA. Requiring MFA on a service role silently breaks it.

### aws:RequestedRegion

```json
"Condition": {
  "StringEqualsIgnoreCase": {
    "aws:RequestedRegion": ["us-east-1", "eu-west-1"]
  }
}
```

- Restricts actions to specific regions.
- Useful for compliance (data residency) and blast-radius control.
- Does NOT apply to global services (IAM, Route 53, CloudFront).
- `StringEqualsIgnoreCase` is recommended — region names are lowercase
  but some tools send mixed case.

### aws:CalledVia

```json
"Condition": {
  "StringEquals": {
    "aws:CalledVia": ["cloudformation.amazonaws.com"]
  }
}
```

- Records the chain of services through which a request passed.
- Use to restrict roles to CloudFormation-initiated calls (prevent direct
  API access outside the pipeline).
- Multi-value: `["cloudformation.amazonaws.com", "lambda.amazonaws.com"]`
  means the request passed through BOTH services in order.

### STS-specific keys (trust policies only)

| Key | Purpose |
|---|---|
| `sts:ExternalId` | Confused-deputy protection for cross-account |
| `sts:RoleSessionName` | Restrict session names |
| `sts:DurationSeconds` | Restrict requested session duration |

```json
"Condition": {
  "StringEquals": {
    "sts:ExternalId": "unique-external-id"
  },
  "NumericLessThan": {
    "sts:DurationSeconds": "3600"
  }
}
```

## Condition operators reference

| Operator | Use case |
|---|---|
| `StringEquals` | Exact string match (case-sensitive) |
| `StringEqualsIgnoreCase` | Exact string match (case-insensitive) |
| `StringLike` | Wildcard match (`*` and `?`) |
| `ArnLike` | ARN match with wildcards |
| `ArnEquals` | Exact ARN match |
| `NumericEquals` | Exact number match |
| `NumericLessThan` | Number < value |
| `NumericLessThanEquals` | Number ≤ value |
| `Bool` | Boolean match — MANDATORY for MFA keys |
| `IpAddress` | CIDR match |
| `DateLessThan` | Date < value (for time-based conditions) |
| `Null` | Check if key is absent/present |
| `ForAllValues:StringEquals` | All values in a multi-value request match |
| `ForAnyValue:StringEquals` | Any value in a multi-value request matches |
| `IfExists` | Suffix: condition evaluates true if key is absent |

## Common condition-key mistakes

1. **Missing `Bool` on MFA condition.** `{"aws:MultiFactorAuthPresent": "true"}`
   silently fails. Use `{"Bool": {"aws:MultiFactorAuthPresent": "true"}}`.

2. **Using `StringEquals` instead of `ArnLike` for ARNs.** ARNs with
   variable components (resource names) need `ArnLike` with wildcards.
   `StringEquals` requires exact match.

3. **`aws:SourceIp` with IPv6.** `aws:SourceIp` does not match IPv6
   addresses. Use `aws:SourceVpc` for IPv6 network scoping.

4. **`ForAllValues` on a single-value key.** `ForAllValues:StringEquals`
   returns true when the key is ABSENT (vacuously true). This is a
   bypass — use `ForAnyValue` or add a `Null` check.

5. **`Null: {key: "false"}` thinking it means "key must be present."**
   `Null: {key: false}` means "key is NOT null" — i.e., key is present.
   But `Null: {key: true}` means "key IS null" — i.e., key is absent.
   The naming is confusing. Test with the policy simulator.

6. **Using `IfExists` as a wildcard.** `...IfExists` means "evaluate
   true if the key is absent." It does NOT make the condition optional.
   Use it when a key may not be present (e.g., `aws:SourceVpce` for
   non-endpoint requests).

## Condition key JSON examples — aws:RequestedRegion, aws:CalledVia (moved from SKILL.md)

**`aws:RequestedRegion` example (multi-region restriction):**
```json
"Condition": {
  "StringEqualsIgnoreCase": {
    "aws:RequestedRegion": ["us-east-1", "eu-west-1"]
  }
}
```

**`aws:CalledVia` example (CloudFormation-only):**
```json
"Condition": {
  "StringEquals": {
    "aws:CalledVia": ["cloudformation.amazonaws.com"]
  }
}
```
