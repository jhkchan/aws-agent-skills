# Eval prompt: distribution-with-static-origin-ready

Design a deployment plan for a Lightsail distribution in front of an
existing Lightsail instance. Emit the standard VERDICT block.

Requirements:

- Distribution name: prod-cdn
- Origin: prod-static-site (Lightsail instance in us-east-1, running,
  reachable on port 80)
- Origin protocol policy: http-only (origin serves HTTP; the
  distribution terminates TLS for viewers)
- Default cache behavior: cache
- TLS: ACM certificate for cdn.example.com (ARN in us-east-1,
  ISSUED, validated yesterday)
- The instance serves static assets (HTML, CSS, JS, images)

Existing-account context: the Lightsail instance prod-static-site
exists in us-east-1, is running, and serves HTTP on port 80 (verified
via `get-instance-state` and `get-instance-port-states`). The ACM
certificate arn:aws:acm:us-east-1:111111111111:certificate/cdn-abc
is ISSUED and covers cdn.example.com. IAM principal holds
lightsail:CreateDistribution.
