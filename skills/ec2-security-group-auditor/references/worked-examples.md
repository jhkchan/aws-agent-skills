# EC2 Security-Group Auditor — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Secondary worked examples (moved from SKILL.md)

- **Database on private CIDR:** SG has `3306 TCP 10.0.0.0/8`. Source is
  RESTRICTED → **RESTRICTED**. Port 3306 is critical ONLY when combined
  with a PUBLIC source.

- **Prefix-list source:** SG has `443 TCP pl-58a543d6` (CloudFront).
  Entries are public AWS edge IPs, but CloudFront is a trusted CDN →
  **PUBLIC_NONCRITICAL** (not OPEN).

- **IPv6 dual-stack (the most-missed exposure):** SG has `22 TCP ::/0`
  with NO IPv4 rule. The model output may look "closed" if the auditor
  only inspects `IpRanges`. `::/0` is PUBLIC, AWS IPv6 addresses are
  globally routable by default, and 22 is CRITICAL → **OPEN**. Always
  iterate BOTH `IpRanges` and `Ipv6Ranges` arrays. A "locked-down on
  IPv4" SG that is wide-open on IPv6 is a common Shadowserver finding.

- **Overlapping CIDR sources (union semantics):** SG has `22 TCP
  0.0.0.0/0` AND `22 TCP 10.0.0.0/8` on the same port. AWS evaluates
  each rule independently — there is no first-match and no deny in
  SGs. The broader `0.0.0.0/0` rule is the effective exposure.
  Per-rule verdicts: OPEN + RESTRICTED → aggregate **OPEN**. Add a
  cleanup note: the `10.0.0.0/8` rule is redundant and obscures
  posture — REMOVE it, do not "narrow" it.

- **Split-horizon evasion:** SG has `443 TCP 0.0.0.0/1` AND
  `443 TCP 128.0.0.0/1`. Neither rule literally equals `0.0.0.0/0`,
  but their union covers the entire IPv4 space. Both are PUBLIC, port
  443 is NON_CRITICAL → **PUBLIC_NONCRITICAL**. This pattern evades
  naive `grep "0.0.0.0/0"` audits; always union complementary halves
  (`/1` pairs, `/2` quads) before classifying.

- **Prefix-list drift between audits:** At review T0, `pl-abcd1234`
  contained only RFC 1918 CIDRs → RESTRICTED. At review T1, the list
  owner added `0.0.0.0/0` to debug a vendor issue. The SG rule itself
  did not change, but the effective verdict flipped to OPEN. Re-fetch
  prefix-list entries on EVERY review cycle; compare `Version` to the
  last-audited value. Drift without a change ticket is itself a finding.
