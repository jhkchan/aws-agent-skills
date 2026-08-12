# Baseline (no-skill) response: copy-data-format-delimiter

---

Your COPY command failed with a delimiter error. The error says
"Delimiter not found" which usually means the data format doesn't
match the COPY command parameters.

Check the data file to see what delimiter it uses. If it's
pipe-separated, change the DELIMITER parameter in your COPY command to
match. Also make sure the FORMAT parameter is correct.

You might also want to check if there are any special characters or
encoding issues in the file that could cause parsing problems.
