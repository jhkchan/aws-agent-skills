# Eval prompt: timeout-db-connection-no-proxy

Diagnose the Lambda timeout for the following function. Walk the
timeout-focused diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-db-connection-no-proxy` started timing out at 10 s after
traffic doubled at the start of a marketing campaign. Logs show
"Connecting to DB" as the last line before each kill. The Aurora
cluster is healthy (CPU 20%, connections 30/500).

```text
FunctionName: fn-db-connection-no-proxy
Qualifier: prod (version 9)
Runtime: python3.12
Timeout: 10
MemorySize: 256
Handler: app.handler
VpcConfig:
  SubnetIds: [subnet-private-a, subnet-private-b]
  SecurityGroupIds: [sg-db]

Function code (excerpt):
  import psycopg2
  def handler(event, context):
      print('Connecting to DB')
      conn = psycopg2.connect(
          host='db.cluster-xxx.us-east-1.rds.amazonaws.com',
          dbname='app', user='app', password='...'
      )
      print('Connected, running query')
      cur = conn.cursor()
      cur.execute('SELECT ...')
      return cur.fetchall()

Recent log pattern (peak-hour timeouts):
  INFO  Connecting to DB
  (no further log line — killed during handshake)
  END RequestId: ... Duration: 10000.00 ms
    Memory Size: 256 MB Max Memory Used: 110 MB
  Task timed out after 10.00 seconds

Off-peak invocations (when concurrency is low):
  INFO  Connecting to DB
  INFO  Connected, running query (Duration so far: 2800 ms)
  INFO  Query complete
  END Duration: 3100 ms (succeeds)

Aurora context:
  - Cluster CPU: 20%, connections: 30 / 500 (not exhausted)
  - Engine: aurora-postgresql, TLS required
  - No RDS Proxy configured
  - Cross-AZ mount: function subnets span us-east-1a and 1b;
    primary is in us-east-1c (cross-AZ handshake adds latency)
```

The function opens a new connection per invocation; the TLS + auth
handshake consumes the budget under concurrency. Identify the layer and
recommend the fix.
