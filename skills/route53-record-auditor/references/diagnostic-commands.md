# Diagnostic Commands — Route 53 Record Auditor

Per-verdict remediation CLI sequences moved verbatim from SKILL.md. Loaded on demand.

## Remediation guidance (per verdict)

### For DANGLING — deleted ALIAS target (Step 1)

1. **Verify** the target resource is deleted:
   - ELB: `aws elbv2 describe-load-balancers --query 'LoadBalancers[?DNSName==\`<dns>\`]'`
   - CloudFront: `aws cloudfront list-distributions --query
     'DistributionList.Items[?DomainName==\`<dns>\`]'`
   - S3: `aws s3api get-bucket-website --bucket <name>` (NXDOMAIN if deleted)
2. If the target is confirmed deleted, **delete or update the record**:
   `aws route53 change-resource-record-sets --hosted-zone-id <id>
   --change-batch file://delete-record.json`
3. If the target was S3 website or API Gateway custom domain and the record
   was in a public zone, **assume potential takeover** during the exposure
   window. Audit for unauthorised requests to the domain.
4. If the target still exists in another region/account, update the ALIAS
   to the correct DNS name or remove the record if it is no longer needed.

### For NO_HEALTH_CHECK — failover PRIMARY (Step 2a)

1. **Create a health check** that tests the primary endpoint:
   ```bash
   aws route53 create-health-check --caller-reference hc-$(date +%s) \
     --health-check-config '{"Type":"HTTPS","FullyQualifiedDomainName":"api.example.com","ResourcePath":"/health","RequestInterval":30,"FailureThreshold":3,"MeasureLatency":true}'
   ```
2. **Associate** the HealthCheckId with the failover PRIMARY record using
   a change-resource-record-sets UPSERT batch.
3. **Verify** the health check is passing:
   `aws route53 get-health-check-status --health-check-id <id>`
4. **Test failover** by stopping the primary endpoint and confirming Route
   53 serves the secondary within the health-check interval (30s default +
   FailureThreshold).

### For NO_HEALTH_CHECK — weighted / latency (Step 2b/2c)

1. Create health checks for each endpoint in the group.
2. Associate HealthCheckId with each record that has `Weight > 0`.
3. Set `EvaluateTargetHealth: true` on ALIAS records within the group so
   Route 53 also considers the target's own health.

### For DNSSEC_GAP — signing disabled (Step 3a)

1. Enable DNSSEC signing:
   ```bash
   aws route53 enable-hosted-zone-dnssec --hosted-zone-id <id>
   aws route53 create-key-signing-key --hosted-zone-id <id> \
     --key-management-service-arn <kms-key-arn> \
     --name <ksk-name> --status ACTIVE
   ```
2. **Publish the DS record** at the parent zone (registrar/TLD). The DS
   value is returned by `aws route53 get-dnssec --hosted-zone-id <id>`.
3. Verify resolver validation with `dig +dnssec <domain>` from an external
   resolver.

### For DNSSEC_GAP — DS record not published (Step 3b)

1. Retrieve the DS record:
   `aws route53 get-dnssec --hosted-zone-id <id>` — copy the `DS` value.
2. Publish it at the domain's registrar (Route 53 registered domains:
   `aws route53domains associate-delegation-signer`).
3. Verify propagation: `dig DS <domain> +short` at the parent TLD.

### For CONFIG_GAP — private IP in public zone (Step 4a)

1. Move the record to a **private hosted zone** associated with the VPC,
   or replace the private IP with the public-facing endpoint (ELB/ALB/CDN).
2. If the record must remain public (e.g., for split-horizon DNS), use a
   separate private zone for internal resolution and keep only public IPs
   in the public zone.

### For CONFIG_GAP — TTL inconsistency (Step 5a)

1. Align all records in the same routing group to the same TTL.
2. Recommended TTLs: 60 for failover/weighted with frequent changes,
   300 for latency/geolocation, 3600 for stable simple-routing records.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after infrastructure changes (new load
   balancers, deleted resources, new routing policies).
3. For public zones, verify the DS record remains published after any KSK
   rollover.
