# Baseline (no-skill) response: open-issue-ec2-degraded

This file captures what a generic assistant produces WITHOUT the
health-event-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, entity-status reasoning).

---

You have an open AWS Health event affecting two EC2 instances. The event
is for degraded EC2 instance performance, and both instances are
currently in an impaired state.

You should check whether the instances are still degraded and consider
stopping and starting them to move to healthy hosts. The event is open
so AWS hasn't resolved it yet.

Health Organizational View is enabled and you have an EventBridge rule,
which is good.
