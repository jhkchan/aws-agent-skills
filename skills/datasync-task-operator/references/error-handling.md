# Error Handling (load on demand) — AWS DataSync Task Operator

The DataSync failure-mode table (ErrorCode/ErrorDetail → root cause →
fix) moved verbatim from SKILL.md. Loaded on demand.

---

## DataSync failure-mode table (moved from SKILL.md)



**DataSync failure-mode table (use during diagnose-failing-execution):**

| Symptom (`ErrorCode` / Status) | Root cause | Fix |
|---|---|---|
| `Status: ERROR`, `ErrorDetail: "Agent is offline"` | Agent VM/EC2 unreachable or stopped | `describe-agent`; restart VM; verify outbound HTTPS 443 to DataSync endpoints. |
| `ErrorDetail: "AccessDenied for s3:PutObject on <dest>"` | Task role missing `s3:PutObject` on destination | Attach policy granting `s3:PutObject` on `arn:aws:s3:::<dest>/*` |
| `ErrorDetail: "Mount target not found"` | EFS/FSx in wrong AZ vs agent subnet | Re-create agent in matching AZ or add mount target in agent subnet |
| `ErrorDetail: "SMB login failed"` | SMB secret expired or rotated | Update Secrets Manager secret; re-create SMB location |
| `ErrorDetail: "KMS key policy does not grant role"` | Destination KMS key policy missing task role | Add `kms:Encrypt`, `kms:GenerateDataKey` grant on destination key policy |
| `VerificationFilesFailed > 0` | Source/destination checksums differ after transfer | Re-run with `VerifyMode: POINT_IN_TIME_CONSISTENT` + `TransferMode: CHANGED`; if persists, investigate destination write path |
| `Status: TRANSFERRING` forever, `BytesTransferred` flat | Network bottleneck, throttling, source saturated | Check `BandwidthLimitInMb`, agent CPU, source disk I/O. Increase agent size or remove throttle. |
| `FilesTransferred` < `EstimatedFilesToTransfer`, `Status: SUCCESS` | Some files skipped via `Includes`/`Excludes` filter (verify intent); if no filter, permission-denied on specific files | Inspect Task Report; widen task role permissions. |
| `Status: LAUNCHING` > 30 min | Agent capacity exhausted (too many queued executions) | Wait; or reduce concurrent tasks on this agent. |


