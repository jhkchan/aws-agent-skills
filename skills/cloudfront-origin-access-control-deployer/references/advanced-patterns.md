# Advanced Patterns (load on demand) — CloudFront Origin Access Control Deployer

Deep-dive material moved verbatim from SKILL.md: the OAC-replaces-OAI heuristic and the 2023-2026 recent-features notes.


---

## Expert heuristic: OAC replaces OAI (moved from SKILL.md)

A baseline model may default to OAI because it is older. The correct
heuristic recognizes that OAC is the successor for all new
distributions.

```text
OAI vs OAC decision:
  ├── New distribution with S3 origin → OAC (always)
  ├── SSE-KMS-encrypted bucket → OAC with sigv4 (OAI does NOT support KMS)
  ├── HTTP POST/PUT to S3 via CloudFront → OAC (OAI only signs GET/HEAD)
  ├── Existing distribution with OAI → migrate to OAC (zero downtime)
  ├── Legacy requirement (OAI only) → OAI (but plan migration)
  └── Custom origin (ALB, EC2, on-prem) → neither (OAC is S3-only)
```

**Key implications:**
- OAI does NOT support SSE-KMS (CloudFront cannot decrypt KMS-encrypted
  objects via OAI). Use OAC with sigv4 signing.
- OAI does NOT support POST/PUT requests (only GET/HEAD). OAC supports
  all HTTP methods. Uploading via CloudFront to S3 requires OAC.
- OAC is a global CloudFront resource (does not need to match the
  bucket region). The S3 origin DomainName must include the region for
  non-us-east-1 buckets.


---

## Step 11 — Recent features (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **OAC general availability (2022-2023):** OAC launched as the
  successor to OAI, adding SSE-KMS and POST/PUT support. AWS
  recommends OAC for all new S3-origin distributions.

- **OAC Terraform support (2023):** The
  `aws_cloudfront_origin_access_control` resource and
  `origin_access_control_id` field enable declarative OAC management.

- **CloudFront continuous deployment (2023-2024):** Enables testing
  distribution changes (including OAC) in staging before production.
  Useful for OAI-to-OAC migration validation.

- **SSE-KMS OAC clarification (2024-2025):** AWS clarified the KMS
  key policy requirements (`cloudfront.amazonaws.com` principal with
  `AWS:SourceArn` condition).

- **CloudFront VPC origin support (2025-2026):** Added VPC origins
  (private origins in a VPC). Separate from OAC (OAC is S3-only).
