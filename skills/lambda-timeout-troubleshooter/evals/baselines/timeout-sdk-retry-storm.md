# Baseline (no-skill) response: timeout-sdk-retry-storm

---

Your Lambda is timing out because DynamoDB is slow. The logs show it
takes 30 seconds and then gets killed. The table is provisioned at 200
WCU which is probably too low for the traffic.

Increase the Lambda timeout to 60 seconds and raise the DynamoDB
WriteCapacityUnits. That should give the function more time to complete
the put operation.
