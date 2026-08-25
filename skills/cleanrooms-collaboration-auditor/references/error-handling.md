# Error Handling — Clean Rooms Collaboration Auditor

Load-on-demand error and edge-case handling moved verbatim from SKILL.md.

## Error and edge-case handling

- **Malformed JSON input:** If the collaboration config is not parseable
  (missing `members` key, unparseable JSON, missing
  `collaborationIdentifier`), emit:
  `VERDICT: ERROR — REASON: <specific defect>. REMEDIATION: Retrieve
  canonical config with aws cleanrooms get-collaboration --output json.`
  Do NOT attempt partial classification on a malformed document.
- **Pagination failure (ThrottlingException):** If `list-collaborations`
  or `list-protected-queries` returns a throttling error mid-pagination,
  retry with exponential backoff: wait 1s, then 2s, then 4s, then 8s
  (max 3 retries). If all retries fail, emit
  `VERDICT: ERROR — REASON: Pagination incomplete due to API throttling
  on page <N>. Epsilon sum may be undercounted.`
  NEVER report OK if pagination was incomplete — the missing pages may
  contain the highest-spend queries. Use `--cli-read-timeout 60
  --cli-connect-timeout 30` on the initial call to reduce mid-stream
  timeouts.
- **Missing cleanroomsml permissions:** If
  `cleanroomsml:GetConfiguredAudienceModel` returns
  `AccessDeniedException`, emit the verdict WITHOUT the audience check
  and add to FINDINGS: `[CONFIG_GAP] Audience model state unknown —
  cleanroomsml:GetConfiguredAudienceModel denied. Cannot verify
  audience readiness.`
