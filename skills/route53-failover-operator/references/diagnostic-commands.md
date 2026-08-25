# Diagnostic Commands — Route 53 Failover Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pagination limits

**Pagination:** `list-resource-record-sets` paginates at 300 record sets
per page — drain `--start-record-name` / `--start-record-type` to
completion for large zones. `list-health-checks` paginates at 100/page.

## Live-account pre-flight command listing

**Live-account pre-flight (skip if offline plan audit):**
1. `aws route53 list-hosted-zones-by-name --dns-name <domain>` — find
   the zone; capture `Id`, `Name`, `Config.Comment`, `ResourceRecordSetCount`.
2. `aws route53 list-resource-record-sets --hosted-zone-id <id>` — find
   the failover records; capture `Type`, `SetIdentifier`, `Failover`
   (PRIMARY/SECONDARY), `TTL`, `ResourceRecords`, `HealthCheckId`,
   `RoutingPolicy`.
3. `aws route53 get-health-check --health-check-id <id>` — capture
   `HealthCheckConfig` (Type, FullyQualifiedDomainName, IPAddress, Port,
   ResourcePath, SearchString, Type, RequestInterval, FailureThreshold),
   `HealthCheckVersion`, and the linked CloudWatch alarm region.
4. `aws route53 get-health-check-status --health-check-id <id>` —
   capture `HealthCheckObservations` (one per Route 53 checker region),
   `Status` (Healthy/Unhealthy/LastKnownGoodStatus).
5. `aws route53 get-health-check-last-failure-reason --health-check-id
   <id>` — capture the most recent failure reason string.
6. `aws route53 test-dns-answer --hosted-zone-id <id> --record-name
   <fqdn> --record-type A --resolver-ip 1.1.1.1` — verify what Route 53
   is currently authoritatively answering. Repeat from multiple
   `--resolver-ip` values (1.1.1.1, 8.8.8.8, 9.9.9.9) to catch
   regional divergence.
7. `aws cloudwatch describe-alarms --alarm-name-prefix <name>` — verify
   an alarm exists on the `AWS/Route53` `HealthCheckStatus` metric for
   this health check ID.
8. For cross-account zones: `aws route53 list-resource-record-sets
   --hosted-zone-id <id> --profile <zone-account-profile>` — verify the
   operator has the cross-account grant.

## Step 3 — pre-state capture and change polling

- Capture pre-state for rollback: `aws route53 list-resource-record-sets
  --hosted-zone-id <id> --output json > /tmp/<id>-rrsets-pre-$(date
  +%s).json` AND `aws route53 test-dns-answer --hosted-zone-id <id>
  --record-name <fqdn> --record-type A --resolver-ip 1.1.1.1 --output
  json > /tmp/<fqdn>-dnsanswer-pre-$(date +%s).json`.
- Execute the change-batch. The API returns `ChangeInfo.Id`; capture
  it for status polling.
- Poll `aws route53 get-change --id <change-id>` until
  `Status: INSYNC` (typically 5-60 seconds).

## Step 4 — post-verification probes

1. `test-dns-answer --hosted-zone-id <id> --record-name <fqdn>
   --record-type A --resolver-ip 1.1.1.1` returns the NEW primary IP.
   Repeat from `8.8.8.8` and `9.9.9.9`.
2. `dig @1.1.1.1 <fqdn> +short` returns the NEW primary IP from at
   least one major public resolver (tolerate cache lag on others).
3. The PRIMARY health check (if applicable) reports `Healthy` for the
   new primary, OR (for failover FROM a down primary) the SECONDARY
   health check reports `Healthy`.
4. Application metric dashboards show traffic shifting to the new
   primary (sample 2x TTL post-change).
5. For weighted failover: confirm the new weight distribution by
   observing traffic share in the metrics.
6. For failover routing: confirm `test-dns-answer` no longer returns
   the old primary IP from any resolver.
