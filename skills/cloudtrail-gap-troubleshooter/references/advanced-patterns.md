# Advanced patterns — CloudTrail Gap Troubleshooter

Edge cases and recent-feature notes moved out of SKILL.md for progressive
disclosure. Load on demand.

## Recent AWS features (2024-2026)

- **CloudTrail Lake (2022 GA, widely adopted 2024-2026):** Managed event
  data store with SQL queries and near-real-time ingestion. Troubleshoot
  Lake gaps by checking the event data store's selector
  (`list-event-data-stores` + `get-event-data-store`).
- **CloudTrail Lake federation (2024):** Federation to Athena/OpenSearch.
  Failures present as "events in Lake but not in Athena" — check federation
  role and Athena workgroup.
- **Enhanced Insights selectors (2024):** `list-insights-selectors` /
  `put-insights-selectors` APIs for per-event-source Insights configuration.
  Legacy `get-insight-selectors` / `put-insight-selectors` still work but
  only toggle global on/off.
- **CloudTrail Organizations auto-enable (2024-2025):** New member accounts
  can auto-receive the org trail without manual `start-logging`.
- **CloudTrail Lake integration with Amazon Q (2025):** Q can query Lake in
  natural language. Verify Q service role has `cloudtrail:StartQuery`.
- **S3 managed bucket policies for CloudTrail (2024):** Console-created
  trails auto-apply the canonical bucket policy. IaC does NOT — include
  the policy explicitly.
- **CloudTrail delete-trail retention (2024):** Deleted trails remain as
  shadow trails for 30 days. `describe-trails --show-shadow-trails`.
