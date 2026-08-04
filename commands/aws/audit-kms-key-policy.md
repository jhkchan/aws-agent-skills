---
description: Audit a KMS key policy and key metadata for cross-account/external principals, wildcard kms:* grants, the kms:Decrypt blast-radius multiplier, rotation status, and key-deletion window exposure.
nl_triggers:
  - "audit this KMS key"
  - "check KMS key policy"
  - "cross-account KMS access"
  - "kms decrypt exposure"
  - "kms wildcard permissions"
  - "key rotation check"
  - "key deletion window"
  - "PendingDeletion KMS"
  - "kms:* to everyone"
  - "Principal star KMS"
  - "encryption key audit"
  - "kms blast radius"
  - "kms:CreateGrant delegation"
  - "hardening KMS key"
routes_to: kms-key-policy-auditor
---

# /aws:audit-kms-key-policy

Activate the `kms-key-policy-auditor` skill and audit one or more KMS key
configurations (key policy + key metadata) for security exposure.

## What it does

Reads a KMS key policy document plus key metadata (KeyManager, KeySpec,
Origin, KeyState, EnableKeyRotation, PendingWindowInDays) and applies the
ordered classification logic:

1. Pre-flight key metadata gate — short-circuit AWS-managed keys,
   asymmetric/HMAC keys (no rotation), and EXTERNAL-origin keys.
2. Key deletion window — PendingDeletion with <= 7 days is CRITICAL
   (imminent irrecoverable data loss; encrypt/decrypt already failing).
3. Principal scope — WILDCARD_PRINCIPAL vs CROSS_ACCOUNT vs SAME_ACCOUNT.
4. Action danger — DATA_ACCESS (Decrypt) vs KEY_CONTROL (PutPolicy,
   ScheduleDeletion) vs DELEGATION (CreateGrant) vs DATA_WRITE vs
   METADATA.
5. Condition strength — kms:ViaService / aws:SourceAccount are STRONG;
   aws:SourceIp 0.0.0.0/0 and aws:Referer are WEAK.
6. Severity matrix — cross-reference principal x action x condition.
7. Rotation status — flag EnableKeyRotation: false on symmetric
   customer-managed keys only.
8. Aggregation — worst finding wins (CRITICAL > HIGH > MEDIUM > OK).

Emits a deterministic VERDICT per key:

```text
KEY: <key-id>
VERDICT: CRITICAL | HIGH | MEDIUM | OK
REASON: <1-2 sentences citing the worst finding and rule number>
FINDINGS:
  - [CRITICAL] <finding description (Rule Na)>
  - [HIGH] <finding description (Rule Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a KMS key policy and metadata and ask any of:

- "audit this KMS key policy"
- "check for cross-account decrypt access"
- "is this key exposed?"
- "what's the blast radius of this key?"
- "is rotation enabled on this key?"
- "is this key pending deletion?"

A bare key ARN or alias + any audit verb ("audit this key", "check key
policy") also routes here via the orchestrator.

## Inputs

- A KMS key policy document (JSON), pasted inline or referenced by file
  path.
- Key metadata: KeyManager, KeySpec, Origin, KeyState, EnableKeyRotation,
  PendingWindowInDays, MultiRegion. These attributes drive the pre-flight
  gate and the rotation/deletion-window dimensions.
- For multi-region keys: provide metadata for each replica independently.

## Outputs

- One VERDICT block per key (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and rule citation.
- Specific remediation: remove cross-account principals, add strong
  conditions, enable rotation, cancel deletion, re-encrypt affected data.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for KMS encryption security).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may have KMS permissions in their identity-based policies.
