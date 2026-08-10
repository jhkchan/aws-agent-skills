# Baseline (no-skill) response: python-exception-attributeerror-script

This file captures what a generic assistant produces WITHOUT the
glue-job-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT + CATEGORY, failing-probe
evidence, passing probes ruled out, specific remediation with CLI).

---

Your Glue job failed with an AttributeError on line 47. The error says
something is None, so probably your DataFrame didn't load correctly.
Check that the table `sales_raw` exists and has data, then add a null
check in your script.

Try re-running after fixing the line:
```python
df = df.withColumn('revenue', col('price') * col('qty'))
```
