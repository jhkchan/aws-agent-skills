# Baseline (no-skill) — activemq-stomp-mqtt-protocols

> This is the response a model produces **without** the skill definition.
> It misses the full multi-protocol surface (OpenWire, STOMP, MQTT, AMQP,
> WS), the security group port requirements for each protocol, the
> broker.xml transport connector configuration, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To create a dev ActiveMQ broker:

```bash
aws mq create-broker \
  --broker-name dev-mq-multi \
  --broker-instance-type mq.t3.micro \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --deployment-mode SINGLE_INSTANCE \
  --users Username=admin,Password=DevPass123,ConsoleAccess=true
```

ActiveMQ supports multiple protocols by default, so you should be good
to go.
