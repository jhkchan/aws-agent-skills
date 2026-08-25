# Error Handling (load on demand) — Direct Connect Auditor

Malformed-topology ERROR block and partial API failure fallback table moved verbatim from SKILL.md.
The primary output contract remains in SKILL.md.

---

## Malformed topology JSON gate (moved from SKILL.md)

**If the topology JSON is malformed** (invalid JSON, missing `connectionId` on
a connection, missing `virtualInterfaceId` on a VIF), output:

```text
CONNECTION: <connection-id or unknown>
VERDICT: ERROR
REASON: Direct Connect topology JSON is malformed or missing required fields — cannot classify.
REMEDIATION: Re-fetch with aws directconnect describe-connections --output json and re-audit.
```

---

## Failure handling — partial API failures and missing fields (moved from SKILL.md)

| Failure mode | Detection | Fallback action |
|---|---|---|
| `describe-bgp-peers` throttled (ThrottlingException) | stderr contains `Throttling` | Retry with exponential backoff (`--max-items 100`, base 2s, max 5 attempts). If still failing, emit `CONFIG_GAP (LOW)` with note `BGP auth state unverifiable — describe-bgp-peers throttled; rerun audit`. Do NOT assume auth is absent. |
| `describe-bgp-peers` returns empty array for a known VIF | VIF exists in `describe-virtual-interfaces` but peers array is `[]` | The VIF has no BGP session configured OR the cross-account view redacted the peers. If `connectionMode: transit` and you are NOT the connection owner, assume redaction — emit `CONFIG_GAP (LOW)` with `Re-audit from partner role`. Otherwise emit `CONFIG_GAP (MEDIUM)` — a VIF with no peers carries no traffic. |
| Required field absent from offline JSON (`authKeyState`, `bgpPeers`, `macSecCapable`) | Field is null or missing | Emit the matching `CONFIG_GAP (LOW)` from the **Reference — Edge-case field handling** table, with the canonical note `Field absent from input — run <api-call> for authoritative value`. NEVER infer a security posture from a missing field. |
| `describe-connection-loa` returns error on a `requested` connection | Non-zero exit or empty response | LOA not yet issued — fall through to Step 3c LOA-stale logic (>5 business days → CONFIG_GAP). |
| API response truncated mid-stream (cross-account >1,000 objects) | Object count exactly 1,000 | Re-fetch with `--max-results 100` and paginate; if pagination unsupported, split by `--connection-id` AFTER the unfiltered pass and diff to detect missing objects. Flag any unrecoverable gap as `CONFIG_GAP (LOW)`. |
