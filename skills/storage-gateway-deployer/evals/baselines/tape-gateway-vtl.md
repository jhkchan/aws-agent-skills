# Baseline (no-skill) — tape-gateway-vtl

> This is the response a model produces **without** the skill
> definition. It activates the gateway and creates tapes but misses
> the tape pool configuration (no Glacier archiving or retention
> lock), does not allocate cache and upload buffer separately, and
> omits the READY_TO_DEPLOY checklist. Generated for with-skill-vs-
> baseline comparison.

---

Activate the Tape Gateway and create virtual tapes:

```bash
aws storagegateway activate-gateway \
  --activation-key TAPEK-99999-VTLXX-88888-YYYYY \
  --gateway-name backup-tape-gateway \
  --gateway-type VTL

aws storagegateway create-tapes \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --tape-size-in-bytes 1073741824000 \
  --num-tapes-to-create 10 \
  --tape-barcode-prefix TAPE \
  --client-token token-12345
```

Then configure your backup software to discover the VTL.
