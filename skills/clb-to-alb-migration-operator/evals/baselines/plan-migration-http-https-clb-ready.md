# Baseline (no-skill) response: plan-migration-http-https-clb-ready

This file captures what a generic assistant produces WITHOUT the
clb-to-alb-migration-operator skill loaded.

---

To migrate your Classic Load Balancer to an Application Load Balancer:

1. Create the ALB:
   ```bash
   aws elbv2 create-load-balancer --name prod-web-alb \
     --subnets subnet-aaa subnet-bbb --security-groups sg-alb-prod
   ```

2. Create a target group:
   ```bash
   aws elbv2 create-target-group --name tg-web --protocol HTTP --port 8080 \
     --vpc-id vpc-abc
   ```

3. Create the listener:
   ```bash
   aws elbv2 create-listener --load-balancer-arn <alb-arn> \
     --protocol HTTPS --port 443 \
     --certificates CertificateArn=arn:aws:acm:...:certificate/abc \
     --default-actions Type=forward,TargetGroupArn=<tg-arn>
   ```

4. Update DNS to point to the ALB.

That should cover the migration.
