# Electric catalog audit — 25 November 2026

The entire active, priced electric catalog was checked from a consistent PostgreSQL read: **2,949 cars / 59 mapped models**. The audit calls the same TypeScript title, fuel and range helpers as the website. Numeric model names such as Zeekr 001/009 are valid; registration year is not compared with the model-year code in a Chinese source title.

## Findings and correction

All cars have a mapped brand/model and a displayable rated electric range. Cycles: 990 NEDC, 1,928 CLTC, 31 WLTC. No missing or conflicting range values, fuel disagreements, lost model names or title/range discrepancies were found.

One stale shared specification was found: listing 60269499, spec 64675, Volkswagen ID.4 CROZZ. The source listing said `2024款 PURE+`, while cached equipment said `2022款 长续航PURE+版`. Fresh Che168 car-info and parameter API responses both confirm the 2024 version and 600 km CLTC. This spec is used by one active listing. Its parameter cache was refreshed on the collector and website, with backups; the original listing title and registration year were preserved. The full subsequent audit reports zero errors and warnings.

Public car-page checks cover one example of every model/measurement-cycle combination (77 pages), checking the mapped full name and exact displayed range against the shared helpers. Results are retained with the task's local audit artifacts.

## Ongoing checks

- `scripts/electric_catalog_audit.mjs` runs inside the deployed container with a read-only PostgreSQL transaction and the exact frontend TypeScript helpers, using Node's bundled type stripping. It does not call Che168 or any paid service.
- `run_electric_catalog_audit.sh` writes `/srv/che168/electric-catalog-audit.json` atomically. A failed or malformed run preserves the last valid report and logs the failure. The report includes its timestamp, counts and affected listing IDs.
- Existing `pull_db.sh` invokes it after an import; the existing hourly translation worker also invokes it. No new schedule or Codex translation automation is created. Audit failures are logged separately and do not roll back a completed catalog import.
- The collector no longer reuses an electric spec cache without valid range data or when its known model year differs from the current source car-info response. Such a cache is fetched again from Che168. The current car-info spec ID takes precedence over a stale listing spec ID. This does not substitute registration year or guess a corrected model.

Automated tests cover stale cache versions, missing/conflicting ranges, fuel conflicts, mapped-name failures, numeric model identifiers and harmless imported-model punctuation. This verifies catalog data consistency; it does not independently measure a used car's actual battery range.
