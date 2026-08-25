# Advanced Patterns (load on demand) — CloudWatch Cross-Account Observability Deployer

Edge-case catalog, expert-knowledge deep dives, and recent AWS feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Edge-case handling (moved from SKILL.md)

- **Link stuck in CREATED not ATTACHED:** the sink policy rejected
  one of the `ResourceTypes`. Check the policy's
  `ForAllValues:StringEquals oam:ResourceTypes` condition.
- **Cross-account metrics missing specific namespace:** the
  `MetricConfiguration.Filter` does not include the namespace.
  Filter syntax is case-sensitive; `AWS/ECS` ≠ `aws/ecs`.
- **Cross-account log groups empty:** the
  `LogGroupConfiguration.Filter` does not match actual log group
  names. Use `prefix("...")`; do not use wildcards.
- **X-Ray service map shows source services disconnected:** the
  `TraceConfiguration.Filter` excludes the downstream service.
  Re-include and `update-link`.
- **Application Signals metrics missing in monitoring account:**
  Application Signals is not enabled in the source account. OAM
  transports but does not enable Application Signals.
- **Managed Grafana queries return empty:** the Grafana data
  source role lacks read permissions on CloudWatch / X-Ray / OAM
  sink, OR the workspace Region differs from the sink Region.
- **AMP cross-account queries 403:** the workspace role trust
  policy does not include the monitoring account principal, or
  the tag condition is mismatched.
- **Sink policy change drops existing links:** removing a source
  account from the sink policy does NOT delete existing links but
  does block updates. Delete the link in the source first.
- **Cross-Region observability:** OAM sinks are Region-scoped.
  Create a sink per Region or use CloudWatch cross-Region metrics
  (separate feature).
---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **CloudWatch cross-account with AMP (2025):** AMP workspace
  cross-account query rules are now configurable via the workspace
  API. OAM does not proxy AMP; the workspace role trust policy is
  the integration point.

- **Cross-account Application Signals (2024-2025):** the
  `AWS::ApplicationSignals::Service` resource type in OAM links
  transports service-level metrics (Latency, Error, Availability,
  Traffic) and service map topology across accounts. Each service
  includes a derived `SourceAccount` dimension for filtering.

- **OAM link filter language enhancements (2024-2025):** the
  filter language supports `prefix("...")` for log group patterns
  and richer `Namespace IN (...)` semantics. Case-sensitivity is
  enforced; previously some namespaces were case-insensitive.

- **AWS Organizations managed sink policies (2024-2025):**
  `aws:PrincipalOrgID` condition on the sink policy auto-includes
  new accounts joining the org. Replaces manual per-account
  principal entries for fleets > 50 accounts.

- **CloudWatch Logs account-level data protection (2024-2025):**
  data-protection masking on log groups propagates through OAM
  links — masked fields stay masked when viewed from the
  monitoring account.

- **Managed Grafana cross-account via OAM (2025):** Grafana
  CloudWatch data source now natively understands the OAM sink;
  the role assumption is transparent. Previously required
  per-account data source entries.

- **Sink-level tagging + OAM StackSets (2024-2025):** sinks
  support `tag-resource` for cost allocation. Link deployment via
  CloudFormation StackSets to fleets of accounts from a single
  template in the monitoring account.
---

## Expert heuristic — designing cross-account observability topology (moved from SKILL.md)

- **One monitoring account per organizational boundary.** Do not
  pile every account into a single sink. Group by business unit,
  environment, or compliance boundary. A sink with > 100 source
  accounts is operationally fragile.
- **Sink Region = observability Region.** Pick the Region where
  your dashboarding lives. Cross-Region aggregation requires
  separate sinks per Region.
- **Org-wide policy for fleets > 50 accounts.** Use
  `aws:PrincipalOrgID` instead of manual per-account entries.
- **Scope link filters narrowly first, broaden on demand.**
  Start with `Namespace IN ("AWS/EC2")` and add namespaces as
  needed. Over-scoping floods the monitoring account.
- **Application Signals cross-account is a two-step enable.**
  Application Signals must be enabled in EACH source account
  before OAM can transport the metrics.
- **AMP cross-account bypasses OAM.** Use workspace role trust
  for AMP. Do not attach an AMP workspace as an OAM resource type.
- **Decommissioning an account.** Delete the link in the source
  account BEFORE removing the source account from the sink policy.
