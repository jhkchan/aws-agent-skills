# Error handling and rollback - S3 Intelligent-Tiering Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Rollback procedure

1. **Restore the prior configuration:**
   ```bash
   aws s3api put-bucket-intelligent-tiering-configuration \
     --bucket <name> --id Config \
     --intelligent-tiering-configuration file://<name>-it-config-backup-<timestamp>.json
   ```
   This stops FUTURE tiering but does not revert objects already moved.

2. **Identify tiered objects** via Storage Lens tier-distribution drift
   or S3 Inventory filtered by storage class.

3. **Restore storage class** via S3 Batch Operations with `S3CopyObject`
   and `TargetStorageClass: STANDARD`. Include copy-request charges in
   the rollback cost estimate.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `list-bucket-intelligent-tiering-configurations` returns empty | `IntelligentTieringConfigurationList: []` | Normal — no configuration present. Proceed with recommendation. |
| `get-storage-lens-configuration` returns `NoSuchConfiguration` | API error | Storage Lens not enabled. Fall back to `list-objects-v2` sample; flag recommendation as MEDIUM confidence. |
| `put-bucket-intelligent-tiering-configuration` fails with `MalformedXML` | API error | JSON schema error. Common cause: `Days` < 90 for ARCHIVE_ACCESS or < 180 for DEEP_ARCHIVE_ACCESS. Validate the configuration and retry. |
| `put-bucket-intelligent-tiering-configuration` fails with `AccessDenied` | API error | Caller role lacks `s3:PutIntelligentTieringConfiguration`. Add the permission to the bucket policy or caller IAM. |
| `list-objects-v2` paginating > 100 pages on a large bucket | Pagination count | STOP iterating live. Use S3 Inventory or Storage Lens aggregate metrics. |
| Storage Lens shows 0 access data on a known-active bucket | Cross-check with CloudTrail `GetObject` events | Storage Lens may be misconfigured. Trust CloudTrail for access-pattern evidence. |

