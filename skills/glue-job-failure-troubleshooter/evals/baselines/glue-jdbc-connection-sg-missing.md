# Baseline (no-skill) response: glue-jdbc-connection-sg-missing

---

Your Glue job can't connect to RDS via JDBC. The connection is timing
out, which usually means a network issue. Check that the RDS instance
is reachable from the subnet where the Glue job runs.

You should also verify the JDBC URL is correct and that the database
credentials are right. If the URL and credentials are fine, it might be
a VPC or routing issue — make sure the Glue job's subnet can route to
the RDS subnet.
