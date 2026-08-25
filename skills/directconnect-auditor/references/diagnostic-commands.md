# Diagnostic Commands (load on demand) — Direct Connect Auditor

Canonical enumeration/pagination commands and pre-flight safety checks moved verbatim from SKILL.md.
The metadata gate short list and classification steps remain in SKILL.md.

---

## Live-account pagination note and canonical enumeration (moved from SKILL.md)

**Live-account pagination note (D2):** `describe-connections` (no
`--connection-id`) and `describe-virtual-interfaces` (no `--connection-id`) are
the only complete listings. Filtering by `--connection-id` misses VIFs whose
underlying connection was swapped. Drain pagination explicitly:

```bash
# Canonical enumeration — DO NOT pass --connection-id (swapped VIFs are missed)
aws directconnect describe-connections         --output json > conns.json
aws directconnect describe-virtual-interfaces  --output json > vifs.json
aws directconnect describe-lags                --output json > lags.json
# DX has no NextToken for these calls; cross-account views truncate at 1,000.
```

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (delete-connection, delete-virtual-interface, update-virtual-interface,
  associate-direct-connect-gateway, MACSec mode change), emit:
  `CONFIRM: About to <action> on <resource>. This affects <consequence>.
  Proceed? (yes/no)` — do NOT execute until the operator confirms. DX
  changes are physical-layer and affect all hybrid traffic.
- **Re-creating a VIF to add BGP auth is destructive.** Capture the current
  config first:
  `aws directconnect describe-virtual-interfaces --virtual-interface-id <id> --output json > /tmp/<id>-backup-$(date +%s).json`.
  VIF configs are not versioned; there is no undo without a backup.
- **MACSec mode change requires both ends.** Switching `no_encrypt` to
  `must_encrypt` requires the CE router to be MACSec-configured first;
  otherwise the link drops and ALL hybrid traffic fails. Confirm CE
  readiness before emitting `update-connection --encryption-mode must_encrypt`.
- **Provisioning a new diverse connection takes weeks.** Do NOT emit
  `create-connection` as an immediate remediation without surfacing the
  lead time. Partner cross-connects typically take 2-6 weeks; LOA issuance
  adds 3-5 business days. The remediation is correct but the operator must
  know the timeline.
- **Direct Connect Gateway creation is global but associations are regional.**
  `create-direct-connect-gateway` is a global call; associating a VGW is
  regional. A misconfigured association leaves the VIF unattached — verify
  with `describe-direct-connect-gateway-attachments` after creation.
- **BGP session re-key is non-disruptive if done via VIF migration.** Provision
  the new VIF with auth, verify BGP up, migrate routes via AS-path prepending,
  then delete the old VIF. Never delete the old VIF first.
