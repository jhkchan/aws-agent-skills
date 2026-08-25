# Error Handling — kms-key-rotation-operator

Failure-mode reference moved verbatim from SKILL.md. Load on demand.

## Rotation failure-mode table (use during diagnose-rotation)


| Symptom | Root cause | Fix |
|---|---|---|
| `enable-key-rotation` returns `InvalidOperationException: ... cannot be performed on a key with KeyUsage SIGN_VERIFY` | Asymmetric key — automatic rotation not supported | Plan manual rotation (create new key + update aliases + re-sign) |
| `enable-key-rotation` returns `InvalidOperationException: ... cannot be performed on a key with Origin EXTERNAL` | Imported key material — KMS cannot rotate | Re-import new material via `get-parameters-for-import` + `import-key-material` |
| `enable-key-rotation` returns `AccessDeniedException` | Key policy denies caller `kms:EnableKeyRotation`, or caller's identity-based policy lacks it | Add `kms:EnableKeyRotation` to the key policy for the caller's role, or call from an authorized role |
| `enable-key-rotation` returns `KMSInvalidStateException: Key is in Disabled state` | Key is `Disabled` | `aws kms enable-key --key-id <id>` first, then enable rotation |
| `enable-key-rotation` returns `KMSInvalidStateException: Key is in PendingDeletion state` | Key scheduled for deletion | `cancel-key-deletion --key-id <id>`, then `enable-key`, then `enable-key-rotation` |
| `enable-key-rotation` returns `InvalidOperationException: ... replica key` | Multi-Region replica — rotation controlled by primary | Call `enable-key-rotation` on the primary key ARN (cross-region if needed) |
| `enable-key-rotation` returns `CloudHsmClusterNotActiveException` | Custom key store's CloudHSM cluster is not `ACTIVE` | Restore the CloudHSM cluster to `ACTIVE`; reconnect the key store |
| `get-key-rotation-status.Enabled: true` but `NextRotationDate` is in the past | Rotation deferred due to KMS internal scheduling or a transient issue | Wait 24 hours; if still overdue, open AWS support |
| `get-key-rotation-status` returns `AccessDeniedException` | Key policy denies caller `kms:GetKeyRotationStatus` | Add `kms:GetKeyRotationStatus` to the key policy for the caller's role |
| CloudTrail shows no `EnableKeyRotation` event but status shows enabled | Rotation was enabled via the console (still logs as `EnableKeyRotation`) or before the trail was created | Verify via `get-key-rotation-status` directly; CloudTrail history is bounded by the trail's retention |
| Applications break after manual rotation (alias updated) | The old key was disabled or deleted before ciphertext was re-encrypted | Re-enable the old key; applications decrypting old ciphertext need the old key `Enabled` |
