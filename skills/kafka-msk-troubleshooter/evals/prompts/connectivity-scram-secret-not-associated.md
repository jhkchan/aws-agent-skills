# Eval prompt: connectivity-scram-secret-not-associated

Diagnose the following Amazon MSK cluster issue. Walk the CONNECTIVITY
diagnostic tree and emit the standard VERDICT block.

## Scenario

An Amazon MSK provisioned cluster
`prod-msk-connectivity-scram-secret-not-associated` in us-east-1.
Producer gets `SASL_AUTHENTICATION_FAILED` when connecting.

## Known facts

- Client uses `security.protocol=SASL_SSL`,
  `sasl.mechanism=SCRAM-SHA-512`.
- `aws kafka describe-cluster` shows:
  `ClientAuthentication.Sasl.Scram.Enabled: true`
- `aws kafka list-scram-secrets --cluster-arn <arn>` returns **empty**
  (no secret associated with the cluster).
- `aws secretsmanager list-secrets --filter Key=name,Values=AmazonMSK_`
  returns: `AmazonMSK_prod_credentials` (secret exists in Secrets
  Manager but is NOT linked to the cluster).
- Broker security groups allow port 9096 (SCRAM) from client SG.
- `openssl s_client -connect <broker>:9096` succeeds (TLS transport OK).
- Cluster `State: ACTIVE`, all brokers HEALTHY, no URP.

## Symptom

SCRAM authentication fails despite the secret existing in Secrets
Manager. The secret is simply not associated with the MSK cluster.
