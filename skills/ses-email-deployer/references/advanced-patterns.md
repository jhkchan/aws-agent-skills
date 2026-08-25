# Advanced Patterns — ses-email-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Edge-case handling

- **Domain identity stuck in Pending:** DKIM CNAME records not
  published or not propagated. Verify with `dig CNAME
  abc123._domainkey.example.com`. Third-party DNS may take longer.
- **DKIM verification fails after CNAME published:** the CNAME
  record name may have `_domainkey` doubled. SES auto-appends the
  domain; do not double it.
- **SPF alignment fails:** the MAIL FROM TXT is missing
  `include:amazonses.com` or `~all` is too strict (`-all` hard
  fails on forwarded mail).
- **DMARC reports show misalignment:** the MAIL FROM domain does
  not match the `From:` header domain. Use the same org domain,
  or set `adkim=r; aspf=r` (relaxed).
- **Bounce notifications not arriving in SNS:** the configuration
  set is not associated with the send (`--configuration-set-name`
  omitted), or the SNS destination is disabled.
- **Dedicated IP throttled:** warmup was skipped or disabled.
  Re-enable automatic warmup and reduce send volume.
- **Template variables not rendering:** `TemplateData` is a JSON
  string, not a JSON object. `{{varName}}` keys must match exactly.
- **Sandbox limit (ThrottlingException):** account is still in
  sandbox. Request production access via the SES console.
- **VPC endpoint private DNS not resolving:** the VPC
  `enableDnsHostnames` and `enableDnsSupport` must both be `true`.
- **Mail Manager ingress not receiving:** the MX record for the
  ingress domain must point at the Mail Manager ingress endpoint,
  NOT the standard SES feedback endpoint.


## Recent AWS features (2024-2026)

- **SES Mail Manager (2024-2025):** a separate SES feature for
  inbound email analysis and egress rule management. Distinct from
  the standard SES sending pipeline. Use `sesv2
  create-email-traffic-policy` and `create-ingress-point`.

- **SES VPC endpoint for sesv2 (2024-2025):** interface VPC
  endpoints support the sesv2 API with private DNS. Enables
  private SES API access from VPCs without internet egress.

- **Virtual Deliverability Manager (2024-2025):** VDM options on
  the configuration set (`VdmOptions`) provide engagement tracking
  and optimized delivery recommendations per-configuration-set.

- **Dedicated IP automatic warmup enhancements (2024-2025):**
  per-IP stage visibility via `get-dedicated-ip` (`WarmupStatus`,
  `WarmupPercentage`). The ramp schedule is tunable.

- **Suppression list account-level management (2024-2025):**
  `put-suppression-attributes` toggles `BOUNCE` / `COMPLAINT`
  suppression at the account level. Per-address management via
  `put-suppressed-destination` / `delete-suppressed-destination`.

- **SES template Handlebars enhancements (2024-2025):** template
  variables support `{{#if}}`, `{{#each}}`, and helpers. Template
  size limit raised to 500 KB (HTML + text).

- **EventBridge integration for SES events (2024-2025):** SES
  event publishing natively supports EventBridge as a destination
  (`EventBridgeDestination`), alongside CloudWatch, SNS, Firehose.

- **SES v2 API as canonical surface (2024-2025):** the v1 SES API
  (`ses`) is in maintenance mode. All new features ship on
  `sesv2`. Migrate from v1 to v2 for configuration sets,
  templates, and suppression list management.


## Expert heuristic — designing SES infrastructure

- **One configuration set per workload type.** Transactional,
  marketing, and onboarding emails have different deliverability
  profiles. Separate sets isolate sender reputation and event
  routing.
- **Dedicated IPs for high volume ( > 100K/day); shared pool for
  low volume.** Dedicated IPs give predictable reputation but
  require warmup. Shared pool is fine for low-volume transactional.
- **Always set a custom MAIL FROM domain.** The default
  `amazonses.com` envelope sender breaks SPF alignment with your
  `From:` header. Custom MAIL FROM enables alignment and improves
  deliverability.
- **DMARC monitoring first, enforcement later.** Publish
  `p=none` with `rua=mailto:...` for 2-4 weeks. Review reports.
  Escalate to `p=quarantine` then `p=reject`.
- **Suppression list on BOUNCE and COMPLAINT.** Suppressing on
  both protects sender reputation. Manual suppression for spam
  traps.
- **Warmup is non-negotiable for dedicated IPs.** Even if you
  migrate an existing workload, the IP is new and needs warmup.
- **SES v2 API is the canonical surface.** All new features ship
  on v2. Migrate from v1 for any new provisioning.

