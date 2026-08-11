# Eval prompt: failover-behaviour-points-at-primary-not-group

Diagnose the CloudFront 502 failure for the following distribution. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Multi-origin distribution returns 502 whenever the primary
origin fails. The secondary origin is healthy but receives zero traffic.
Operators expected automatic failover.

```text
DistributionId: E4QW3R4Y5Z6A7D
DomainName: d444444defghi1.cloudfront.net
PrimaryOrigin: primary.failover-behaviour-points-at-primary-not-group.example.com
SecondaryOrigin: secondary.failover-behaviour-points-at-primary-not-group.example.com

aws cloudfront get-distribution-config output (excerpt):
  Origins:
    Items:
      - Id: primary
        DomainName: primary.failover-behaviour-points-at-primary-not-group.example.com
      - Id: secondary
        DomainName: secondary.failover-behaviour-points-at-primary-not-group.example.com
  OriginGroups:
    Items:
      - Id: group-1
        FailoverCriteria:
          StatusCodes:
            Items: [500, 502, 503, 504]
        Members:
          Items:
            - OriginId: primary
            - OriginId: secondary
  DefaultCacheBehavior:
    TargetOriginId: primary   # WRONG: should be group-1

curl primary origin directly:
  → Connection refused (primary is down)
curl secondary origin directly:
  → HTTP/1.1 200 OK (secondary is healthy)

CloudFront access logs show only primary-origin fetches;
  secondary origin never contacted.
```

The OriginGroup is defined and the failover criteria are correct, but
the DefaultCacheBehavior routes traffic to the single primary origin
instead of the group. Failover never triggers.
