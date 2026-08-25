# Worked Examples — STS Cross-Account Role Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Edge case walkthroughs

Concrete worked examples for the most commonly mis-classified patterns. An
agent should apply these patterns when the classification steps produce an
ambiguous result.

### Edge 1: ForAllValues trap on aws:SourceArn

```json
{
  "Principal": {"Service": "lambda.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "ForAllValues:StringEquals": {
      "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:my-fn"
    }
  }
}
```

**Analysis:** `ForAllValues:StringEquals` evaluates TRUE when the request
contains zero matching values. If Lambda does not populate `aws:SourceArn`
on certain internal code paths (e.g., service-invoked functions, edge
optimizations), the key is absent and the condition passes — granting
access to any caller, including confused-deputy exploitation.

**Verdict:** EXTERNAL_TRUST (Step 4) — the condition is a bypass, not a
guard.

**Remediation:** Replace with `ArnLike` (which requires the key to be
present and match):
```json
"Condition": {"ArnLike": {"aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"}}
```

### Edge 2: Mixed strong + weak condition keys

```json
{
  "Principal": "*",
  "Action": "sts:AssumeRole",
  "Condition": {
    "IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
    "StringEquals": {"aws:SourceAccount": "123456789012"}
  }
}
```

**Analysis:** Two condition operators at the same level are ANDed — both
must be true. `aws:SourceAccount` (STRONG) requires the request to
originate from account 123456789012. `aws:SourceIp` (WEAK for RFC1918)
restricts to a private CIDR. The strong key dominates — classify as
CONDITIONAL. The `aws:SourceIp` is redundant but does not weaken the
strong key.

**Verdict:** CONDITIONAL (Step 2 — wildcard principal with strong condition).

### Edge 3: Multi-statement aggregation — mixed verdicts

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/app-role"},
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
      "Action": "sts:AssumeRole",
      "Condition": {"StringEquals": {"sts:ExternalId": "opaque-id-12345"}}
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Analysis:** Statement 1 is OK (same-account scoped). Statement 2 is
CONDITIONAL (cross-account with ExternalId). Statement 3 is WILDCARD_TRUST
(Principal `"*"` with no condition). Per Step 9 aggregation, the role-level
verdict is the worst: WILDCARD_TRUST.

**Verdict:** WILDCARD_TRUST / CRITICAL.

**Remediation:** Remove Statement 3 immediately (containment). Statement 2
is acceptable if the ExternalId is opaque and rotated on relationship
change. Statement 1 requires no change.

### Edge 4: Role chaining and aws:PrincipalTag ABAC bypass

```json
{
  "Principal": {"AWS": "*"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {"aws:PrincipalTag/Team": "data-engineering"}
  }
}
```

**Analysis:** `aws:PrincipalTag/Team` reads the assuming principal's session
tags. If an attacker can assume an intermediate role that allows
`sts:TagSession` with `Team=data-engineering` (role chaining), they inject
the tag and satisfy this condition. The trust policy trusts attacker-
controlled data.

**Verdict:** WILDCARD_TRUST / CRITICAL — the condition is bypassable via
role chaining. `Principal: "*"` gated by `aws:PrincipalTag` is not a
security boundary.

**Remediation:** Replace `Principal: "*"` with a specific account or role
ARN. Do not rely on `aws:PrincipalTag` as the sole guard for wildcard
principals — the tag source must be admin-set (not session-injected) and
the tag-setting roles must themselves be audited for `sts:TagSession`
exposure.

### Edge 5: SAML federated trust with valid vs missing condition

Valid (constrained):
```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRoleWithSAML",
  "Condition": {
    "StringEquals": {
      "SAML:sub": "corp-ad:data-engineering-group",
      "SAML:aud": "https://signin.aws.amazon.com/saml"
    }
  }
}
```
**Verdict:** CONDITIONAL — the IdP controls who can assert, and the
condition narrows the accepted assertions to a specific subject and
audience.

Missing condition (dangerous):
```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRoleWithSAML"
}
```
**Verdict:** EXTERNAL_TRUST — any assertion from the IdP that matches the
provider ARN is accepted. The IdP admin (or anyone who compromises the
IdP) controls access to your AWS role.

### Edge 6: Action-principal mismatch (silent failure)

```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRole"
}
```

**Analysis:** This statement is invalid. SAML federated principals require
`sts:AssumeRoleWithSAML`, not `sts:AssumeRole`. The combination silently
fails at runtime — no principal can assume the role via this statement. Flag
as a misconfiguration.

**Verdict:** ERROR with reason "Action-principal mismatch:
`sts:AssumeRole` cannot be used with a Federated principal — use
`sts:AssumeRoleWithSAML` for SAML or `sts:AssumeRoleWithWebIdentity` for
OIDC."

## Multi-statement aggregation example

```text
ROLE: multi-trust-role
VERDICT: WILDCARD_TRUST
REASON: Statement 1 (Principal: {"AWS": "arn:aws:iam::123456789012:role/internal-app"} on same account) is OK. Statement 2 (Principal: "*" with no condition) is WILDCARD_TRUST — anyone with AWS credentials can assume this role. Role verdict is the worst statement (Step 9 aggregation).
RISK: CRITICAL
REMEDIATION: Remove Statement 2 entirely. If public access was never intended, this is a critical misconfiguration — rotate all credentials exposed via this role immediately and audit CloudTrail for unauthorized AssumeRole events.
```
