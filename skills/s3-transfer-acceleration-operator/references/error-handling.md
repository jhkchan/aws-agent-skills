# S3 Transfer Acceleration Operator — Error Handling and Failure Modes

Transfer failure modes and fixes, moved verbatim from SKILL.md. Use during diagnose-transfer and when a pre-check fails.

**Transfer failure-mode table (use during diagnose-transfer):**

| Symptom | Root cause | Fix |
|---|---|---|
| Accelerated upload is slower than direct | Source and bucket are in the same region (no benefit) or source is near the bucket region | Disable acceleration for same-region transfers; use direct endpoint |
| `put-bucket-accelerate-configuration` returns `UnsupportedArgument` | Bucket is a directory bucket (S3 Express One Zone) | Directory buckets do not support acceleration; use the Express One Zone endpoint directly |
| Accelerated upload returns `PermanentRedirect` | Using the wrong endpoint format; accelerate endpoint requires virtual-hosted-style | Use `<bucket>.s3-accelerate.amazonaws.com`; ensure SDK has `use_accelerate_endpoint: true` |
| `upload-part` to accelerate endpoint fails after disable | Acceleration was disabled while multipart upload was in-flight | Re-enable acceleration, complete or abort the multipart upload, then disable |
| Acceleration enabled but no speed improvement | Client is using the standard endpoint, not the accelerate endpoint | Update the SDK configuration: `use_accelerate_endpoint: true` or use `<bucket>.s3-accelerate.amazonaws.com` |
| Checksum mismatch on accelerated multipart upload | Parts uploaded out of order or part-size mismatch | Use consistent part size (except last part); upload all parts before calling complete-multipart-upload |
| `AccessDenied` on accelerate endpoint | Bucket policy restricts access to specific endpoints or VPC endpoints | Add the accelerate endpoint to the bucket policy's allowed sources |
| Cost higher than expected | Downloads are also billed via accelerate endpoint; large data OUT | Use accelerate for uploads only; serve downloads via CloudFront or standard endpoint |
| IPv6 connection fails on accelerate endpoint | Not using dualstack endpoint | Use `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6 |
| KMS throttling during accelerated multipart upload | Each part triggers a KMS GenerateDataKey call; many parallel parts overwhelm KMS | Request a KMS quota increase, or use a KMS key data key reuse period of 5+ minutes |

