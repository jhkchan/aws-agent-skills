# Baseline (no-skill) response: verify-cutover-completed

This file captures what a generic assistant produces WITHOUT the
clb-to-alb-migration-operator skill loaded.

---

Your migration looks complete. The Route 53 weights show 100% ALB and
0% CLB, and your targets are healthy. You can now delete the CLB.

```bash
aws elb delete-load-balancer --load-balancer-name prod-web-clb
```
