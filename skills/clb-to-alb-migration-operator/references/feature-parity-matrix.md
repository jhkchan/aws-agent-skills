# CLB-to-ALB Feature Parity Matrix Reference

Load this reference when planning a CLB-to-ALB migration to map every
Classic Load Balancer feature to its Application Load Balancer equivalent
(or to flag features with no ALB equivalent that require NLB).

## Listener protocols

| CLB protocol | ALB equivalent | Notes |
|---|---|---|
| `HTTP` | ALB listener `HTTP` | Direct map. ALB adds X-Forwarded-Proto. |
| `HTTPS` | ALB listener `HTTPS` | Requires SSL cert (ACM or IAM). ALB adds SNI. |
| `TCP` | NONE on ALB — use NLB | ALB is HTTP/HTTPS only. TCP listeners must migrate to NLB. |
| `SSL` (TCP passthrough) | NONE on ALB — use NLB | SSL passthrough requires NLB with TCP/SSL listener. |

## SSL/TLS certificates

| CLB source | ALB action | Notes |
|---|---|---|
| `arn:aws:acm:...` (ACM-issued) | Reuse the same ARN on ALB listener | ACM certs are regional; the ALB must be in the same region. Auto-renewal is free. |
| `arn:aws:iam::...:server-certificate/...` (IAM-uploaded) | Re-issue via ACM, OR re-import to ACM | IAM certs have NO managed renewal. Plan to re-issue via ACM before or during migration. |
| Self-signed / third-party CA | Import to ACM | ACM supports imported certs (no managed renewal for imports). |

## SSL policies

| CLB policy | ALB equivalent | Notes |
|---|---|---|
| `ELBSecurityPolicy-2016-08` (legacy) | `ELBSecurityPolicy-TLS13-1-2-2021-06` | Migrate to TLS 1.3; CLB maxed at TLS 1.2. |
| `ELBSecurityPolicy-TLS-1-2-2017-01` | `ELBSecurityPolicy-TLS13-1-2-2021-06` | ALB supports TLS 1.3 with forward secrecy. |
| Custom policy | Custom `SSLPolicy` via `create-ssl-policy` | Rare; prefer AWS-managed policies. |

## Sticky sessions

| CLB policy | ALB target group attribute | Notes |
|---|---|---|
| `LBCookieStickinessPolicy` (lb-generated cookie) | `stickiness.enabled=true`, `stickiness.type=lb_cookie`, `stickiness.duration_seconds=<timeout>` | Both generate an `AWSELB` cookie. ALB cookie is per-target-group. |
| `AppCookieStickinessPolicy` (app cookie name) | `stickiness.type=app_cookie`, `stickiness.app_cookie.cookie_name=<name>` | ALB honors the application cookie; `duration_seconds` is fallback only. |
| No stickiness | `stickiness.enabled=false` | Default. |

## Connection draining / deregistration

| CLB attribute | ALB target group attribute | Notes |
|---|---|---|
| `ConnectionDraining.enabled: true`, `ConnectionDraining.timeout: 300` | `deregistration_delay.timeout_seconds: 300` | Match the value exactly. Default is 300 on both. |
| `ConnectionDraining.enabled: false` | `deregistration_delay.timeout_seconds: 0` | Immediate deregistration. Rare; usually keep 300. |

## Cross-zone load balancing

| CLB attribute | ALB behavior | Notes |
|---|---|---|
| `CrossZoneLoadBalancing.enabled: true` | Always on (ALB) | No action needed. |
| `CrossZoneLoadBalancing.enabled: false` | Always on (ALB) | Behavior change — traffic spreads evenly across AZs post-cutover. Pre-scale targets if any AZ was under-provisioned. |

## Access logs

| CLB attribute | ALB attribute | Notes |
|---|---|---|
| `AccessLog.enabled: true`, `AccessLog.S3BucketName`, `AccessLog.S3BucketPrefix`, `AccessLog.EmitInterval: 5` | `access_logs.s3.enabled=true`, `access_logs.s3.bucket`, `access_logs.s3.prefix`, `access_logs.s3.enabled=true` | ALB log format differs from CLB. Update Athena/Loki queries. ALB logs include `target_status_code`, `target_processing_time`, `error_reason` — richer than CLB. |

## Idle timeout

| CLB attribute | ALB attribute | Notes |
|---|---|---|
| `ConnectionSettings.IdleTimeout: 60` | `idle_timeout.timeout_seconds: 60` (load balancer attribute) | Direct map. Default 60s on both. |

## Proxy Protocol

| CLB policy | ALB equivalent | Notes |
|---|---|---|
| `ProxyProtocolPolicyType` (Proxy Protocol v1/v2) | NONE — ALB does NOT emit Proxy Protocol | Backends must read `X-Forwarded-For` (client IP), `X-Forwarded-Proto` (scheme), `X-Forwarded-Port`, `X-Forwarded-Host`. ALB always injects these headers on HTTP/HTTPS listeners. For Proxy Protocol v2 binary frames, the backend listener must be reconfigured. |

## Health checks

| CLB health check | ALB target group health check | Notes |
|---|---|---|
| `Target: HTTP:8080/healthz` | `HealthCheckProtocol: HTTP`, `HealthCheckPort: 8080`, `HealthCheckPath: /healthz` | CLB combined port+path in `Target`; ALB separates them. |
| `Target: TCP:443` | `HealthCheckProtocol: HTTPS`, `HealthCheckPath: /`, `HealthCheckPort: 443` | CLB TCP health check = TCP handshake success. ALB HTTPS health check = HTTP 200 on path. Plan a path that returns 200. |
| `Interval: 30`, `Timeout: 5`, `HealthyThreshold: 3`, `UnhealthyThreshold: 3` | `HealthCheckIntervalSeconds: 30`, `HealthCheckTimeoutSeconds: 5`, `HealthyThresholdCount: 3`, `UnhealthyThresholdCount: 3` | Direct map. |
| `Matcher: 200` (implicit) | `Matcher.HttpCode: 200` (explicit) | ALB matcher is explicit. Use `200` or `200-299`. |

## Tags

CLB tags (`describe-tags`) should be replicated onto the ALB and target
groups via `create-tags`. Tags do not migrate automatically.

## Features CLB lacks that ALB adds

These are post-migration gains — call them out in the plan as positives:

- **Path-based routing:** `/api/*` to one target group, `/static/*` to
  another, default to a third. CLB routed all traffic to one backend.
- **Host-based routing:** `api.example.com` to one TG, `www.example.com`
  to another, on the same ALB.
- **HTTP header / query string / method routing:** advanced listener
  rules.
- **OIDC authentication:** `authenticate-cognito` or `authenticate-oidc`
  action — no API Gateway needed for auth.
- **WAF attachment:** AWS WAF Web ACL on the ALB for SQLi/XSS/bot.
- **Lambda targets:** ALB invokes Lambda directly (no API Gateway).
- **HTTP/2 and gRPC:** ALB supports HTTP/2 multiplexing and gRPC routing.
- **TLS 1.3:** ALB supports `ELBSecurityPolicy-TLS13-1-2-2021-06`.
- **Weight-based target group forwarding:** native blue/green without
  Route 53.
- **Zonal shift:** evacuate a single AZ during regional impairment.
