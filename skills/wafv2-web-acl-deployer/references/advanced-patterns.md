# Advanced Patterns - wafv2-web-acl-deployer

## Recent AWS features 2024-2026 (moved from SKILL.md)

- **Challenge action (2021, expanded 2024-2025):** silent browser
  challenge for low-friction bot filtering. Returns HTTP 202 with
  JavaScript; browsers solve in ~5 seconds. Custom request handling
  and AWS WAF JavaScript SDK integration expanded.

- **CAPTCHA action (2021, expanded 2024-2025):** interactive
  CAPTCHA for high-confidence abuse. Token lifetime configurable;
  mobile SDK support expanded.

- **ATP GA (2021-2024):** managed rule group for credential
  stuffing and brute force. Configurable login path, field
  identifiers, payload type. Integrates with threat-intel feeds.

- **ACFP GA (2022-2024):** managed rule group for abusive signup
  detection. Configurable signup path and registration fields.

- **Aggregate key types expanded (2024):** rate-based rules now
  support `URI`, `QUERY_STRING`, `HTTP_METHOD`, `HEADER` as
  aggregate keys in addition to `IP` and `FORWARDED_IP`.

- **Bot Control category overrides (2024):** finer-grained
  per-category overrides (allow Googlebot, block scrapers).

- **JSON body parsing (2024):** `JsonBody` field-to-match with
  `MatchPattern` and `MatchScope` for inspecting JSON request
  bodies without regex.

- **Token domains (2024-2025):** CAPTCHA / Challenge tokens can
  be shared across multiple Web ACLs in the same account/Region,
  reducing user friction across properties.

## Expert heuristic - choosing scope, rules, and actions (moved from SKILL.md)

**Scope — CloudFront vs Regional:** determined by the target
resource. CloudFront distribution = CLOUDFRONT scope (always in
us-east-1). Everything else = REGIONAL scope in the resource's
Region. There is no "global" REGIONAL ACL — replicate per Region.

**Managed rules — start with the Core Rule Set:**
`AWSManagedRulesCommonRuleSet` is the right default for any
public-facing workload. Add `SQLiRuleSet` for database endpoints,
`LinuxRuleSet`/`WindowsRuleSet` based on target OS, and
`AmazonIpReputationList` for threat-intel blocking. Add Bot
Control and ATP only when you have a clear bot /
credential-stuffing problem — they are billed per request.

**Custom rules — allow-lists first, blocks last:** put partner IP
allows and known-good path allows at the lowest priorities
(0-9). Put workload-specific blocks (geo, URI, size) at high
priorities (1000+). This ensures legitimate partners are not
caught by managed rule groups.

**Actions — Count before Block:** always run a new rule in Count
mode for 1-2 weeks. Inspect the CloudWatch metric and sampled
requests. If the false-positive rate is acceptable, switch to
Block. For bot defense, use Challenge first (low friction), then
CAPTCHA if Challenge is insufficient.

**Rate limiting — choose the aggregate key carefully:** for
direct-to-AWS connections, use `IP`. For traffic behind a CDN, ALB,
or proxy, use `FORWARDED_IP` with `X-Forwarded-For` and
`Position: FIRST`. For per-endpoint rate limits, use `URI` or
scope-down with `ByteMatchStatement`.

**Logging — Kinesis Firehose is the default:** Firehose buffers and
batches to S3 with the least operational overhead. CloudWatch Logs
is fine for low-volume (<1000 req/s) alerting. Direct S3 is not
supported — Firehose is the intermediary.

**ATP / ACFP — pin login and signup paths:** ATP requires
`LoginPath`, `UsernameField.Identifier`, `PasswordField.Identifier`,
and `PayloadType` (JSON or FORM_ENCODED). ACFP requires
`RegistrationPath` and the same field identifiers. Wrong paths
silently disable the rule group.

## Edge-case handling (moved from SKILL.md)

- **Wrong scope discovered after creation.** The scope is immutable.
  Delete the Web ACL and recreate with the correct scope.
  Associations are removed on deletion. CloudFront association
  requires a distribution update.

- **Rule matches but no Block fires.** Check the rule's action — it
  may be `Count` (non-terminating). Check priority — a higher-
  priority `Allow` rule may be winning. Check `ExcludedRules` in
  the managed rule group.

- **Rate-based rule never triggers.** Verify the aggregate key. If
  using `IP` behind a CDN, switch to `FORWARDED_IP`. Verify the
  `Limit` is requests per 5 minutes. Verify `ScopeDownStatement`
  is not over-narrowing.

- **Logging silently drops logs.** Verify the Firehose name starts
  with `aws-waf-logs-`. Verify the destination resource policy
  allows `delivery.logs.amazonaws.com`. Check Firehose CloudWatch
  metrics for `DeliveryToS3.Success`.

- **CAPTCHA interstitial does not render.** The client-side AWS WAF
  JavaScript SDK must be integrated. The token cookie domain must
  match the site domain. Verify the action is `CAPTCHA` not
  `Challenge` (Challenge is silent).

- **Web ACL exceeds WCU budget.** Each Web ACL has a WCU limit
  (1500 default, 3000 on request). Bot Control (~50 WCUs), ATP
  (~50 WCUs), and large regex rules consume the most. Reduce by
  excluding rules within managed groups, or request a limit
  increase.
