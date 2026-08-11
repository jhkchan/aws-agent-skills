# Eval prompt: connectivity-sg-blocking-port-9094

Diagnose the following Amazon MSK cluster issue. Walk the CONNECTIVITY
diagnostic tree and emit the standard VERDICT block.

## Scenario

An Amazon MSK provisioned cluster
`prod-msk-connectivity-sg-blocking-port-9094` in us-east-1. Producers
and consumers report `TimeoutException` connecting to bootstrap brokers.

## Known facts

- `aws kafka get-bootstrap-brokers` returns:
  `BootstrapBrokerStringTls: b-1.xxx.kafka.us-east-1.amazonaws.com:9094,...`
- Client uses `security.protocol=SSL` on port 9094.
- Client security group: `sg-aaa`. Broker security group: `sg-bbb`.
- `aws ec2 describe-security-groups --group-ids sg-bbb` shows:
  - Inbound rule: port 9092 (PLAINTEXT) allowed from `sg-aaa`.
  - **No inbound rule for port 9094 (TLS).**
- `telnet b-1.xxx.kafka.us-east-1.amazonaws.com 9094` times out.
- `telnet b-1.xxx.kafka.us-east-1.amazonaws.com 9092` succeeds (but
  client needs TLS, not PLAINTEXT).
- `aws kafka describe-cluster` shows `State: ACTIVE`, all brokers
  HEALTHY. No URP.

## Symptom

All clients using TLS (port 9094) time out. PLAINTEXT (port 9092) works
but is not acceptable for production.
