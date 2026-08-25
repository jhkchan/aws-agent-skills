# Advanced Patterns — GuardDuty Finding Automator

Load-on-demand detail moved verbatim from SKILL.md.

## Step 0: Expert knowledge — non-obvious GuardDuty + EventBridge behaviors — moved from SKILL.md

- **EventBridge `detail.severity` may serialize as string or number**
  depending on detector version. Numeric matching rules can fail
  silently. Test with a sample event; when in doubt, route ALL findings
  to Lambda and branch internally on `detail.finding.severity`.

- **Finding IDs are stable across updates.** GuardDuty updates the
  existing finding and increments `service.eventCount`. EventBridge
  emits on every update. Track processed IDs in DynamoDB (7-day TTL).

- **`archive-findings` does NOT delete.** Archived findings remain
  queryable for 90 days. Suppression filters archive automatically but
  do not prevent EventBridge emission if applied after the initial emit.

- **Security Hub auto-enables GuardDuty as a source** when both are
  enabled in the same Region. Custom enrichment via `BatchImportFindings`
  creates a SEPARATE finding — deduplicate on finding ID to avoid dups.

- **WAF IP set limits: 10,000 IPs per set, 200 sets per ACL.** Blocking
  every GuardDuty source IP exhausts the limit within weeks. Use a
  rotating IP set (TTL eviction) or NACL-based blocking for high volume.

- **Organizations delegated admin is Region-specific.** Each Region
  requires its own designation. Deploy the pipeline via StackSets.

- **Lambda remediation timeout must be at least 60 seconds.** EC2 SG
  swap takes 10-30 seconds to propagate. The default 3-second timeout
  is insufficient.

- **Cross-account event bus routing is required for multi-account.**
  Member-account findings emit to the member's default bus. Configure
  forwarding to the delegated admin's bus.

## Step 11: CloudTrail correlation for TTPs — moved from SKILL.md

A single finding is an event. A sequence of findings is an attack chain.

| Chain pattern | MITRE tactic | Finding sequence |
|---|---|---|
| Recon → Initial Access | TA0043 → TA0001 | `Recon:EC2/PortProbe` → `UnauthorizedAccess:EC2/SSHBruteForce` |
| Initial Access → Persistence | TA0001 → TA0003 | `UnauthorizedAccess:EC2` → `Persistence:IAMUser/NewUserCreation` |
| Persistence → Exfiltration | TA0003 → TA0010 | `Backdoor:EC2` → `Exfiltration:S3/ObjectExfiltration` |
| Impact | TA0040 | `CryptoCurrency:EC2/BitcoinTool` (single, high confidence) |

```python
def correlate_ttps(finding, dynamodb_table):
    """Check for related findings within 60-min window."""
    related_types = get_related_ttps(finding['type'])
    recent = dynamodb_table.query(
        KeyConditionExpression='resource_id = :rid',
        FilterExpression='finding_type IN :types AND #ts > :cutoff',
        ExpressionAttributeValues={':rid': finding['resource']['resourceId'],
                                   ':types': related_types,
                                   ':cutoff': (datetime.utcnow() - timedelta(minutes=60)).isoformat()})
    if recent['Items']:
        chain = [i['finding_type'] for i in recent['Items']] + [finding['type']]
        return f"TTP chain detected: {' -> '.join(chain)}"
    return None
```

## Recent AWS features (2024-2026) — moved from SKILL.md

- **Runtime Monitoring for ECS/EKS (2024 GA):** Runtime-level detection.
  Findings of type `Runtime/EKS/*`, `Runtime/ECS/*`. Remediation should
  isolate the task/pod, not the host.

- **Malware Protection for EBS (2024):** Automated malware scan of
  flagged volumes. Wire AFTER isolation — scan the snapshot, not the
  live volume. `THREATS_DETECTED` should page on-call.

- **EKS Protection (2024-2025):** Kubernetes API-level detection.
  Remediation: revoke K8s RBAC token or isolate pod via Lambda + EKS API.

- **Security Hub custom actions (2024):** Console-button custom actions
  triggering Lambda — analyst-initiated remediation without EventBridge.

- **EventBridge global endpoints (2024-2025):** Multi-region failover
  for event-driven remediation pipelines.

- **Organizations auto-enable enhancements (2025):** `--auto-enable`
  now covers Runtime Monitoring and Malware Protection for new accounts.

## Expert heuristic: severity-based auto-response blast radius — moved from SKILL.md

A single misconfigured EventBridge rule with a Lambda that auto-isolates
on all findings can quarantine every EC2 instance in an account within
minutes — including the one running the Lambda itself.

> ALWAYS test GuardDuty auto-remediation in a non-production account
> first, and scope every EventBridge rule with an explicit finding-type
> AND severity filter. Never deploy a Lambda that auto-isolates on all
> finding types against an unbounded resource population.

**Scoping techniques:**

| Technique | Mechanism | Limit |
|---|---|---|
| Finding-type filter | `detail.type` in rule | Restricts to specific families |
| Severity threshold in Lambda | Internal branch on `severity` | Low/Medium never triggers containment |
| Resource-tag scope | Check instance tags before isolating | Only `auto-remediate: enabled` |
| Account isolation | Sandbox account only | Zero production exposure |
| Lambda reserved concurrency | `--reserved-concurrent-invocations 10` | Caps simultaneous actions |

**3-phase validation:**

1. **Phase 1 — DRY (notify only):** Deploy in non-prod with NOTIFY ONLY.
   Generate test findings. Monitor 1 week.
2. **Phase 2 — CONTAINMENT in non-prod:** Enable containment. Test on
   sandbox instances. Verify rollback. Monitor for FPs.
3. **Phase 3 — DRY in prod:** Deploy to prod in NOTIFY ONLY. Monitor
   2 weeks. If < 1% FP, enable containment for Critical/High only.

**Finding ID deduplication:**

```python
# DynamoDB: guardduty-processed-findings, PK: finding_id, TTL: 7 days
def is_already_processed(finding_id, table):
    return 'Item' in table.get_item(Key={'finding_id': finding_id})
```

**Post-deploy alarms:** Lambda Errors > 0, DLQ depth > 0, GuardDuty
Critical/High count increasing without Security Hub finding (broken
pipeline). All should page on-call.

**Surface in output:** `BLAST_RADIUS: <scope>` and
`VALIDATION_STATUS: <phase-1-dry | phase-2-containment | prod-dry |
prod-containment>`. If not `prod-containment`, do NOT mark as deployable.
