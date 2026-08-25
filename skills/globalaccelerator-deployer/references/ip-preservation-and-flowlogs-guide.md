# Client IP Preservation and Flow Logs Reference

Supplementary reference for the Global Accelerator Deployer skill.
Use when planning client IP preservation per endpoint type, origin
security group posture, or flow log destination configuration.

## Client IP preservation matrix

The "client IP" the origin sees depends on endpoint type and the
`PreserveClientIpEnabled` setting. This is NOT a global toggle — it
is per-endpoint-type.

| Endpoint type | PreserveClientIpEnabled | L4 source IP at origin | Header at origin | Origin SG scope |
|---|---|---|---|---|
| ALB | N/A (no toggle) | AWS GA IP (from `51.224.0.0/14`) | `X-Forwarded-For: <client-IP>` | GA prefix pool |
| NLB | `false` (default) | AWS GA IP (from `51.224.0.0/14`) | (none; L4 source is GA IP) | GA prefix pool |
| NLB | `true` | Real client IP | (none; L4 source IS client IP) | Client CIDR ranges |
| EC2 | `false` (default) | AWS GA IP (from `51.224.0.0/14`) | (none) | GA prefix pool |
| EC2 | `true` | Real client IP | (none) | Client CIDR ranges |
| Elastic IP | N/A (EIP is endpoint) | Real client IP (preserved by definition) | (none) | Client CIDR ranges |
| Custom routing endpoint | N/A (always preserved) | Real client IP | (none) | Client CIDR ranges |

## GA prefix pool (2026)

When `PreserveClientIpEnabled` is false (or N/A for ALB), origins see
source IPs from the GA-managed prefix pool. Add this CIDR to the
origin security group inbound rules.

- **IPv4:** `51.224.0.0/14` (covers `51.224.0.0` to `51.227.255.255`)
- **IPv6:** not currently documented; check AWS docs for the latest
  pool before scoping IPv6 SGs.

Verify the current pool via `aws globalaccelerator list-byoip-cidrs`
(for your own BYOIP ranges) or AWS documentation (for the Amazon-managed
pool). The pool may expand over time — set up a quarterly review.

## Decision tree: when to enable PreserveClientIpEnabled

```
Origin needs to see real client IP?
├─ NO
│   └─ PreserveClientIpEnabled: false (default for NLB, EC2)
│        Origin SG scopes to 51.224.0.0/14. Simpler SG management.
│
└─ YES
    ├─ Why?
    │   ├─ IP-based rate limiting at origin
    │   ├─ Geo-blocking at origin (WAF rule by country)
    │   ├─ Application logs must reflect real client IP
    │   └─ Security analytics / forensics by client IP
    │
    └─ PreserveClientIpEnabled: true
         Origin SG MUST allow client CIDR ranges (e.g., 0.0.0.0/0
         for global public, or a specific corporate CIDR for internal).
         Update SG in the SAME deploy as the GA change.
```

**Anti-pattern:** NEVER enable `PreserveClientIpEnabled: true` without
updating the origin SG in the same deploy. A GA deploy that enables
preservation but leaves the SG scoped to the GA prefix pool cuts off
ALL traffic — the origin sees client IPs but the SG only allows the
GA pool.

## ALB endpoint: reading the client IP

For ALB endpoints, the client IP is **always** available in the
`X-Forwarded-For` header. The ALB sees the AWS GA IP at L4 (because
GA terminates the TCP flow and opens a new one to the ALB), but the
ALB inserts the real client IP into `X-Forwarded-For`.

**Application code must read the header**, not the L4 socket source:

```python
# CORRECT
client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()

# WRONG (returns AWS GA IP, not the client IP)
client_ip = request.remote_addr
```

For ALB target groups behind the ALB, the same applies — read
`X-Forwarded-For`. Configure the ALB to preserve the header chain
(default) rather than overwriting.

## NLB endpoint: PreserveClientIpEnabled behavior

When `PreserveClientIpEnabled: true` for an NLB endpoint:
- The NLB receives traffic with the real client IP at L4.
- The NLB target group sees the real client IP at L4.
- The origin (EC2 instance behind the NLB) sees the real client IP at
  L4 (socket source IP).
- Security groups at every layer (NLB SG, target SG) MUST allow the
  client CIDR ranges, not just the GA prefix pool.

When `PreserveClientIpEnabled: false`:
- The NLB receives traffic with an AWS GA IP at L4.
- The NLB target group sees the AWS GA IP.
- The origin sees the AWS GA IP.
- Security groups can scope to `51.224.0.0/14`.

**Caveat:** NLB does not insert `X-Forwarded-For` by default. To
preserve the client IP at L7 behind an NLB, enable target group
attribute `proxy_protocol_v2.enabled` (Proxy Protocol v2) — the origin
reads the client IP from the PPv2 header. This is independent of GA's
PreserveClientIpEnabled.

## EC2 endpoint: PreserveClientIpEnabled behavior

EC2 endpoints behave identically to NLB endpoints (the EC2 instance
IS the L4 target). When `PreserveClientIpEnabled: true`:
- The EC2 instance sees the real client IP at L4 (socket source IP).
- The EC2 instance SG MUST allow client CIDR ranges.

When `false`:
- The EC2 instance sees the AWS GA IP at L4.
- The EC2 instance SG can scope to `51.224.0.0/14`.

EC2 endpoints are **single-AZ** — the instance lives in one AZ. For
HA, deploy instances across AZs and use endpoint weights to load
balance, or front the instances with an NLB (NLB is multi-AZ).

## Flow logs — CloudWatch Logs destination

```bash
aws globalaccelerator update-accelerator-attributes \
  --accelerator-arn <arn> \
  --flow-logs-log-group "/aws/globalaccelerator/prod-ga" \
  --flow-logs-s3-bucket ""
```

**Required permissions:**
- The `AWSServiceRoleForGlobalAccelerator` service-linked role must
  have `logs:CreateLogStream` and `logs:PutLogEvents` on the log
  group ARN. The service-linked role is auto-created on first GA use;
  if it was deleted, GA recreates it on the next operation.
- The log group must exist before configuring flow logs (GA does not
  create it).

**Log entry shape:**
Each entry captures: timestamp, accelerator ARN, listener ARN,
endpoint group ARN, endpoint ID, client IP, client port, endpoint
IP, endpoint port, protocol, byte count, packet count. Useful for
traffic analysis, anomaly detection, and capacity planning.

## Flow logs — S3 destination

```bash
aws globalaccelerator update-accelerator-attributes \
  --accelerator-arn <arn> \
  --flow-logs-s3-bucket "prod-ga-flowlogs" \
  --flow-logs-log-group ""
```

**Required S3 bucket policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "flowlogs.globalaccelerator.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::prod-ga-flowlogs/*"
  }]
}
```

**S3 logging path:**
`s3://<bucket>/AWSLogs/<account-id>/globalaccelerator/<region>/<year>/<month>/<day>/`

Use Athena or S3 Select to query historical flow logs. For long-term
retention (compliance), add an S3 Lifecycle policy to transition to
Glacier after 90 days.

**Anti-pattern:** NEVER configure flow logs to S3 without verifying
the bucket policy. GA silently drops logs on permission errors —
there is no status field in the accelerator indicating "logging
failed." Verify by sending test traffic and checking for log objects
within 5 minutes.

## Flow log destination decision

| Destination | Use case | Cost |
|---|---|---|
| CloudWatch Logs | Real-time analysis, CloudWatch Insights queries, alerting on flow patterns | $0.50/GB ingested + $0.03/GB stored |
| S3 | Long-term retention, Athena queries, compliance archives | $0.023/GB stored (Standard); less with Lifecycle to Glacier |
| Both (separate accelerators) | Real-time + long-term | Cost additive |

For most production deployments, **S3 is the default** — lower cost
at scale and better for compliance retention. CloudWatch is preferred
when you need real-time alerting on flow patterns (e.g., DDoS
detection via CloudWatch Logs Insights).

## Verifying flow log delivery after deployment

```bash
# CloudWatch: verify log streams appear
aws logs describe-log-streams \
  --log-group-name /aws/globalaccelerator/prod-ga \
  --order-by LastEventTime \
  --descending \
  --limit 5

# S3: verify objects appear
aws s3 ls s3://prod-ga-flowlogs/AWSLogs/111111111111/globalaccelerator/ \
  --recursive | head -10

# Send test traffic through the accelerator
curl -v https://<anycast-ip>/
```

If no logs appear within 5 minutes of test traffic:
1. Verify the destination permission (service-linked role / bucket policy).
2. Verify the accelerator is `DEPLOYED` (not `IN_PROGRESS`).
3. Verify the listener and endpoint groups are healthy
   (`list-endpoint-groups` shows endpoints as `HEALTHY`).
4. Open a support ticket if all of the above pass — there may be a
   regional flow-log pipeline delay.

## Cross-account endpoints (2024+) — RAM resource share detail

For cross-account endpoints, the **workload account** (where the
endpoint ALB/NLB/EC2 lives) creates the RAM resource share and
invites the **network account** (where the accelerator lives). The
network account accepts the invitation. Then `add-endpoints` in the
network account references the workload-account endpoint ARN; GA
resolves it via the share.

**Permission flow:**
```
Workload account (222222222222)
  ├─ Owns the ALB
  ├─ Creates RAM resource share for the ALB ARN
  └─ Invites network account (111111111111)

Network account (111111111111)
  ├─ Accepts the RAM invitation
  ├─ Creates the accelerator
  ├─ Creates listener + endpoint group
  └─ Calls add-endpoints with the workload ALB ARN
       GA resolves via the share; if PENDING or REJECTED, returns AccessDeniedException
```

**Share state machine:**
- `PENDING` — invitation sent, not accepted. `add-endpoints` fails.
- `ACTIVE` — invitation accepted. `add-endpoints` succeeds.
- `REJECTED` — invitation explicitly rejected. `add-endpoints` fails.
- `EXPIRED` — invitation not accepted within 12 days. `add-endpoints` fails.
- `DELETING` / `DELETED` — share removed. Existing endpoints remain
  but new `add-endpoints` calls fail.

Always verify share state via
`aws ram get-resource-share-invitations --resource-arns <endpoint-arn>`
before adding cross-account endpoints.

---

### Step 6: Flow logs — CloudWatch Logs or S3 (moved from SKILL.md)

**CloudWatch Logs:**

```bash
aws globalaccelerator update-accelerator-attributes \
  --accelerator-arn <arn> \
  --flow-logs-s3-bucket "" \
  --flow-logs-log-group "/aws/globalaccelerator/prod-ga"
```

The `AWSServiceRoleForGlobalAccelerator` service-linked role needs
`logs:CreateLogStream` and `logs:PutLogEvents` on the log group ARN.
Verify via `iam:get-role` and check the attached policy.

**S3 destination:**

```bash
aws globalaccelerator update-accelerator-attributes \
  --accelerator-arn <arn> \
  --flow-logs-s3-bucket "prod-ga-flowlogs" \
  --flow-logs-log-group ""
```

**S3 bucket policy (required):**

```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "flowlogs.globalaccelerator.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::prod-ga-flowlogs/*"
  }]
}
```

**Anti-pattern:** NEVER configure flow logs without verifying the
destination permission. GA silently drops logs on permission errors —
there is no status field indicating "logging failed." Verify by sending
test traffic and checking for log entries within 5 minutes.

## Expert heuristic: choosing client IP preservation per endpoint type (moved from SKILL.md)

The "right" client IP preservation setting is a function of endpoint
type and the origin's security model. The heuristic below resolves it.

| Endpoint | Default | When to enable | Origin SG posture |
|---|---|---|---|
| ALB | Always X-Forwarded-For (no toggle) | N/A — header-based | Scope to GA pool (`51.224.0.0/14`); WAF at ALB sees real client IP |
| NLB | `false` (recommended) | Origin has IP-based controls (WAF, rate limit, geo-block by CIDR) | `true`: allow client CIDRs; `false`: scope to GA pool |
| EC2 | `false` (recommended) | Application reads L4 source IP for logs or IP-based rules | `true`: allow client CIDRs; `false`: scope to GA pool |
| Elastic IP | N/A (EIP is the endpoint) | Client IP preserved at L4 by definition | Origin SG scope unchanged |

**Decision rules:**
- Default `PreserveClientIpEnabled: false` for NLB and EC2 unless the
  origin has explicit IP-based controls. Simpler SGs; trade-off is
  origin logs show AWS GA IPs.
- When `true`, update the origin SG in the SAME deploy. GA enabling
  preservation without an SG update cuts off all traffic.
- For custom routing accelerators, client IP is always preserved at L4
  — no toggle exists.
- The GA prefix pool is `51.224.0.0/14` (IPv4, 2026). Verify via
  `aws globalaccelerator list-byoip-cidrs` before scoping SGs; the pool
  may expand over time.

ALWAYS emit the client IP preservation decision as a PRE_CHECKS row
naming the endpoint ARN, the setting, and the SG posture
(client-ranges vs GA-pool).

