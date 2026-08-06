---
description: Audit a VPC Lattice service network for auth-policy absence (default-open), public Principal:"*" Invoke grants, NotAction inverse-wildcard traps, cross-account exposure, target group security, and RAM share coverage.
nl_triggers:
  - "audit this VPC Lattice service network"
  - "check lattice auth policy"
  - "is my service network public"
  - "vpc lattice cross-account access"
  - "lattice target group security"
  - "lattice RAM share audit"
  - "no auth policy on service network"
  - "vpc-lattice:Invoke exposure"
  - "lattice service network security"
  - "Principal star lattice"
  - "NotAction lattice auth"
  - "lattice auth policy"
  - "service network auth"
  - "hardening lattice service network"
routes_to: vpc-lattice-auth-auditor
---

# /aws:audit-vpc-lattice-auth

Activate the `vpc-lattice-auth-auditor` skill and audit one or more VPC Lattice
service network configurations for security exposure.

## What it does

Reads a VPC Lattice auth-policy document plus service-network metadata
(associations, services, target groups, RAM shares) and applies the ordered
classification logic:

1. Auth-policy presence — NOT_SET means default-open (any resource in an
   associated VPC can invoke services).
2. Principal scope — WILDCARD_PRINCIPAL vs CROSS_ACCOUNT vs SAME_ACCOUNT.
3. Action danger — INVOKE_ACCESS (vpc-lattice:Invoke, vpc-lattice:*, *,
   NotAction inverse wildcard) vs CONTROL_ACCESS vs METADATA.
4. Condition strength — aws:SourceVpc/aws:SourceAccount are STRONG;
   aws:SourceIp 0.0.0.0/0 is WEAK.
5. Verdict matrix — cross-reference principal x action x condition.
6. Target group security — IP targets outside VPC CIDR are CONFIG_GAP.
7. Cross-account RAM share — verify auth policy covers consumer account.
8. Service-level auth-policy override — evaluate independently.
9. Aggregation — worst finding wins.

Emits a deterministic VERDICT per service network:

```text
SERVICE NETWORK: <sn-id>
VERDICT: NO_AUTH_POLICY | PUBLIC_SERVICE_NETWORK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and rule number>
FINDINGS:
  - [PUBLIC_SERVICE_NETWORK] <finding description (Rule Na)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a VPC Lattice service network configuration and ask any of:

- "audit this VPC Lattice service network"
- "is my service network public?"
- "check lattice auth policy"
- "what's the blast radius of this service network?"
- "is the auth policy configured?"
- "is cross-account lattice access secured?"

A bare service network ID or ARN + any audit verb also routes here.

## Inputs

- A VPC Lattice auth-policy document (JSON), pasted inline or referenced by
  file path.
- Service-network metadata: auth-policy state (NOT_SET or ACTIVE), VPC
  associations, services, target groups (type, targets, VPC), RAM resource
  shares.
- For services with their own auth policies: provide each service-level
  policy independently.

## Outputs

- One VERDICT block per service network (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding verdict and rule/step citation.
- Specific remediation: attach scoped auth policy, replace wildcard
  principals, add conditions, remove external IP targets, scope RAM shares.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for VPC Lattice security).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may have vpc-lattice:Invoke permissions in their identity-based policies.
