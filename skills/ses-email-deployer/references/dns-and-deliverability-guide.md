# DNS records and deliverability guide — deep reference

This reference covers DKIM CNAME layout, MAIL FROM MX + SPF per
Region, DMARC policy stages, dedicated IP warmup schedule, the
full NEVER list, and edge-case handling. Load when designing or
troubleshooting SES email deliverability.

## DKIM CNAME layout

SES generates 3 DKIM tokens per domain identity. Each token maps
to a CNAME record:

| Record name | Record type | Record value |
|---|---|---|
| `<token1>._domainkey.example.com` | CNAME | `<token1>.dkim.amazonses.com` |
| `<token2>._domainkey.example.com` | CNAME | `<token2>.dkim.amazonses.com` |
| `<token3>._domainkey.example.com` | CNAME | `<token3>.dkim.amazonses.com` |

### Common CNAME mistakes

- **Double `_domainkey`:** SES auto-appends `_domainkey`. If you
  publish `<token>._domainkey.example.com._domainkey.example.com`,
  verification never succeeds. The record name is
  `<token>._domainkey.example.com` only.
- **Missing trailing dot in Route 53:** Route 53 auto-appends the
  zone name; do not include it in the record name.
- **Third-party DNS with CNAME flattening:** some providers flatten
  CNAME to A records. SES DKIM requires a true CNAME.
- **TTL too high:** SES polls the records; a TTL > 3600 delays
  verification. Use TTL 1800 or lower.

## MAIL FROM MX + SPF per Region

The MAIL FROM domain (`mail.example.com`) requires two records:

1. **MX record** pointing at the Region-specific SES feedback
   endpoint.
2. **TXT record** with the SPF policy.

### MX endpoints by Region

| Region | MX endpoint |
|---|---|
| us-east-1 | `feedback-smtp.us-east-1.amazonses.com` |
| us-west-2 | `feedback-smtp.us-west-2.amazonses.com` |
| eu-west-1 | `feedback-smtp.eu-west-1.amazonses.com` |
| eu-central-1 | `feedback-smtp.eu-central-1.amazonses.com` |
| ap-south-1 | `feedback-smtp.ap-south-1.amazonses.com` |
| ap-southeast-1 | `feedback-smtp.ap-southeast-1.amazonses.com` |
| ap-southeast-2 | `feedback-smtp.ap-southeast-2.amazonses.com` |
| ap-northeast-1 | `feedback-smtp.ap-northeast-1.amazonses.com` |
| ap-northeast-2 | `feedback-smtp.ap-northeast-2.amazonses.com` |
| ap-northeast-3 | `feedback-smtp.ap-northeast-3.amazonses.com` |
| ca-central-1 | `feedback-smtp.ca-central-1.amazonses.com` |
| sa-east-1 | `feedback-smtp.sa-east-1.amazonses.com` |

### SPF TXT record formats

| Policy | TXT value | Effect |
|---|---|---|
| Soft fail (recommended) | `v=spf1 include:amazonses.com ~all` | Forwarded mail passes with warning |
| Hard fail | `v=spf1 include:amazonses.com -all` | Forwarded mail fails SPF |
| Monitoring only | `v=spf1 include:amazonses.com ?all` | No enforcement; log only |

Use `~all` (soft fail) for the MAIL FROM domain. Forwarded mail
breaks SPF because the forwarder's IP is not in `include:amazonses.com`.
Hard fail (`-all`) causes legitimate forwarded mail to be rejected.

## DMARC policy stages

DMARC is published at `_dmarc.example.com` as a TXT record. The
policy has three enforcement levels:

### Stage 1: Monitor (`p=none`)

```
v=DMARC1; p=none; rua=mailto:dmarc@example.com; pct=100; adkim=s; aspf=s
```

Publish this for 2-4 weeks. Aggregate reports (`rua`) arrive daily
with SPF / DKIM alignment statistics. No enforcement; mail flows
normally.

### Stage 2: Quarantine (`p=quarantine`)

```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; pct=100; adkim=s; aspf=s
```

Mail failing DMARC alignment is sent to spam / junk folder.
Monitor bounce and complaint rates. If alignment is clean for
2+ weeks, escalate to reject.

### Stage 3: Reject (`p=reject`)

```
v=DMARC1; p=reject; rua=mailto:dmarc@example.com; pct=100; adkim=s; aspf=s
```

Mail failing DMARC alignment is rejected at the receiving server.
This is the strongest enforcement. Use only after clean quarantine
stage.

### DMARC tags

| Tag | Meaning | Values |
|---|---|---|
| `p` | Policy for the domain | `none`, `quarantine`, `reject` |
| `sp` | Policy for subdomains | `none`, `quarantine`, `reject` |
| `pct` | Percentage of mail subject to policy | `0`-`100` |
| `rua` | Aggregate report destination | `mailto:` URI |
| `ruf` | Forensic report destination | `mailto:` URI |
| `adkim` | DKIM alignment mode | `s` (strict), `r` (relaxed) |
| `aspf` | SPF alignment mode | `s` (strict), `r` (relaxed) |
| `fo` | Forensic report options | `0`, `1`, `d`, `s` |

### Alignment modes

- **Strict (`adkim=s`, `aspf=s`):** the DKIM `d=` domain and the
  SPF MAIL FROM domain must exactly match the `From:` header
  domain.
- **Relaxed (`adkim=r`, `aspf=r`):** the organizational domain
  must match. Subdomains are acceptable.

Use strict alignment for transactional email where the `From:`
header and MAIL FROM domain are the same. Use relaxed if you send
from subdomains (`news@example.com` with MAIL FROM
`mail.example.com`).

## Dedicated IP warmup schedule

SES automatic warmup ramps volume per IP over ~45 days:

| Day | Volume per IP | Cumulative |
|---|---|---|
| 1 | 100 | 100 |
| 2 | 200 | 300 |
| 3 | 400 | 700 |
| 4 | 800 | 1,500 |
| 5 | 1,600 | 3,100 |
| 6 | 3,200 | 6,300 |
| 7 | 6,400 | 12,700 |
| 8 | 12,800 | 25,500 |
| 9 | 25,600 | 51,100 |
| 10+ | Doubles daily until target | - |

Check warmup status:

```bash
aws sesv2 get-dedicated-ip --ip 10.0.0.1 --region us-east-1
```

`WarmupStatus`: `IN_PROGRESS` → `DONE`. `WarmupPercentage` shows
the ramp progress (0-100).

### Warmup mistakes

- **Disabling warmup mid-cycle:** resets the reputation build. The
  IP is treated as new by inbox providers.
- **Sending above the warmup schedule:** SES throttles to the
  warmup cap. If you need higher volume, wait for the ramp.
- **Sharing warmed-up IPs across workloads:** mixing transactional
  and marketing email on the same IP dilutes reputation. Use
  separate pools.
- **Migrating warmed IPs between Regions:** not supported. Each
  IP is Region-scoped.

## Full NEVER list

1. NEVER send from an unverified domain identity. SES rejects with
   `MessageRejected`.
2. NEVER disable dedicated IP warmup on a new IP. Let automatic
   warmup run the full cycle.
3. NEVER use `-all` (hard fail) in the SPF record for the MAIL FROM
   domain. Use `~all`.
4. NEVER omit `--configuration-set-name` on the send call if you
   need event publishing.
5. NEVER publish DMARC `p=reject` on day one. Start with `p=none`,
   escalate to `quarantine` then `reject`.
6. NEVER double the `_domainkey` segment in the DKIM CNAME record
   name. SES auto-appends it.
7. NEVER use the wrong Region's MX endpoint for the MAIL FROM
   domain. Each Region has a unique feedback endpoint.
8. NEVER mix transactional and marketing email on the same IP pool
   without separate configuration sets.
9. NEVER leave bounce / complaint notifications unmonitored. Wire
   an SNS destination and process feedback to maintain reputation.
10. NEVER suppress on bounce `type=undefined` (temporary bounce).
    Suppress only on permanent bounces.
11. NEVER assume the SES v1 API receives new features. Migrate to
    `sesv2` for any new provisioning.
12. NEVER skip the production access request. Sandbox limits sends
    to verified addresses at 1/sec and blocks real sends.

## Edge-case handling (extended)

### Domain identity stuck in Pending

DKIM CNAME records not published or not propagated. Verify:

```bash
dig CNAME abc123._domainkey.example.com +short
```

Should return `abc123.dkim.amazonses.com`. Third-party DNS may
take longer than Route 53 (up to 72 hours in rare cases).

### DKIM verification fails after CNAME published

The CNAME record name may have `_domainkey` doubled, or the
trailing dot is missing. SES auto-appends the domain; do not
double it. Check with `dig` to confirm the CNAME resolves.

### SPF alignment fails

The MAIL FROM TXT is missing `include:amazonses.com` or `~all` is
too strict. Use `dig TXT mail.example.com +short` to verify the
SPF record includes the SES include.

### DMARC reports show misalignment

The MAIL FROM domain does not match the `From:` header domain.
Use the same organizational domain, or set `adkim=r; aspf=r`
(relaxed alignment) if sending from subdomains.

### Bounce notifications not arriving in SNS

The configuration set is not associated with the send
(`--configuration-set-name` omitted), or the SNS destination is
disabled. Verify with `aws sesv2 get-configuration-set
--configuration-set-name <name>`.

### Dedicated IP throttled

Warmup was skipped or disabled. Re-enable automatic warmup and
reduce send volume. Check `WarmupStatus` and `WarmupPercentage`.

### Template variables not rendering

`TemplateData` is a JSON string, not a JSON object. The
`{{varName}}` syntax must match the keys in `TemplateData`
exactly. Handlebars helpers (`{{#if}}`, `{{#each}}`) require
matching closing tags.

### Sandbox limit (ThrottlingException)

Account is still in sandbox. Request production access via the SES
console (Account dashboard → "Request production access"). Sandbox
limits sends to verified addresses at 1/sec.

### VPC endpoint private DNS not resolving

The VPC `enableDnsHostnames` and `enableDnsSupport` must both be
`true`. Private DNS for interface endpoints requires these VPC
settings.

### Mail Manager ingress not receiving

The MX record for the ingress domain must point at the Mail Manager
ingress endpoint, NOT the standard SES feedback endpoint. Mail
Manager has its own ingress analysis pipeline.

### Bounce type filtering

SES bounce notifications include `bounceType` (`Permanent` or
`Transient`) and `bounceSubType`. Suppress only on `Permanent`
bounces. Transient bounces (e.g., `MailboxFull`) should not
trigger suppression.
