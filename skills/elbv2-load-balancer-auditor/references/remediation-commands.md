# ELBv2 Load Balancer Auditor — remediation commands (load on demand)

Per-verdict remediation CLI, moved verbatim from SKILL.md.

## Remediation guidance — per-verdict CLI (moved verbatim from SKILL.md lines 491-586)


### For INSECURE_LISTENER — TLS 1.0/1.1 policy (Step 1)

1. Update the listener SslPolicy to a TLS 1.2+ policy:
   ```bash
   aws elbv2 modify-listener --listener-arn <arn> \
     --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 --profile <p>
   ```
2. Verify the new policy is applied:
   ```bash
   aws elbv2 describe-listeners --listener-arns <arn> \
     --query 'Listeners[0].SslPolicy' --profile <p>
   ```
3. Test with an external TLS scanner (ssllabs.com, testssl.sh) to confirm no
   client can negotiate TLS 1.0 or 1.1.

### For INSECURE_LISTENER — HTTP-only with no HTTPS (Step 1)

1. Add an HTTPS listener on port 443 with a TLS 1.2+ SslPolicy and an ACM
   certificate.
2. Change the HTTP:80 listener to redirect to HTTPS:
   ```bash
   aws elbv2 modify-listener --listener-arn <http-arn> \
     --default-actions Type=redirect,RedirectConfig.Protocol=HTTPS,\
   RedirectConfig.Port=443,RedirectConfig.StatusCode=HTTP_301 --profile <p>
   ```

### For PERMISSIVE_SG — over-exposed security group (Step 2)

1. Identify the listener ports the LB actually uses (e.g., 80, 443).
2. Remove SG rules that open non-listener ports to 0.0.0.0/0:
   ```bash
   aws ec2 revoke-security-group-ingress --group-id <sg-id> \
     --ip-permissions IpProtocol=tcp,FromPort=0,ToPort=65535,\
   IpRanges=[{CidrIp=0.0.0.0/0}] --profile <p>
   ```
3. Add SG rules scoped to the exact listener ports:
   ```bash
   aws ec2 authorize-security-group-ingress --group-id <sg-id> \
     --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,\
   IpRanges=[{CidrIp=0.0.0.0/0}] --profile <p>
   ```
4. For internal LBs, replace 0.0.0.0/0 with the VPC CIDR or known ranges.

### For NO_ACCESS_LOGS — access logs disabled (Step 3)

1. Create or identify an S3 bucket with the correct policy granting
   `elasticloadbalancing.amazonaws.com` write access.
2. Enable access logs:
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=access_logs.s3.enabled,Value=true \
     Key=access_logs.s3.bucket,Value=<bucket> \
     Key=access_logs.s3.prefix,Value=<prefix> --profile <p>
   ```
3. Verify log delivery after 5–10 minutes by listing the S3 prefix.

### For IDLE — zero healthy targets (Step 4)

1. Determine whether the LB is still needed:
   `aws elbv2 describe-tags --resource-arns <arn>` — check for ownership tags.
2. If the LB is abandoned, delete it (disable deletion protection first if
   enabled):
   ```bash
   aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
     --attributes Key=deletion_protection.enabled,Value=false --profile <p>
   aws elbv2 delete-load-balancer --load-balancer-arn <arn> --profile <p>
   ```
3. If the LB is needed but targets were deregistered by accident, re-register:
   ```bash
   aws elbv2 register-targets --target-group-arn <tg-arn> \
     --targets Id=<instance-id>,Port=<port> --profile <p>
   ```

### For CONFIG_GAP — cross-zone off (NLB, Step 5)

```bash
aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true --profile <p>
```
Note: enabling cross-zone on NLB incurs inter-AZ data transfer charges.

### For CONFIG_GAP — deletion protection off (Step 5)

```bash
aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn> \
  --attributes Key=deletion_protection.enabled,Value=true --profile <p>
```

### For OK

No remediation required for the current posture. Recommend:
- Periodic SslPolicy review as AWS releases new policies.
- Verify the S3 bucket policy for access logs is intact (log-delivery
  silent-failure check).
- For ALB: associate a WAFv2 Web ACL for defense-in-depth (ALB only).
