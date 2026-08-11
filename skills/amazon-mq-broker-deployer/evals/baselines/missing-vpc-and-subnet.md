# Baseline (no-skill) — missing-vpc-and-subnet

> This is the response a model produces **without** the skill definition.
> It fails to detect the missing prerequisites (VPC, subnet, security
> group, LDAP directory, configuration) and instead jumps to CLI commands
> that would fail at runtime. Generated for with-skill-vs-baseline
> comparison.

---

To create an ActiveMQ broker for order events:

```bash
aws mq create-broker \
  --broker-name orders-mq \
  --broker-instance-type mq.t3.micro \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --deployment-mode active/standby \
  --users Username=admin,Password=MyPassword123,ConsoleAccess=true
```

You might also want to enable encryption and logs. Let me know if you
need help with that.
