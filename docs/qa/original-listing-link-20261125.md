# Original listing link — 25 November 2026

Car detail pages display “Оригинал объявления на Che168” below the key parameters, including cars without a seller description. The link uses the stored `cars.url`, opens a new tab and uses `noopener noreferrer`. The original-language text disclosure remains separate.

Only HTTP(S) addresses on che168.com/www.che168.com whose path ends in the current listing ID are accepted. Addresses are normalized to HTTPS and tracking queries/fragments removed. All 44,205 active priced listings have an accepted, matching original URL. This validates the stored destination; it does not claim every third-party page is currently accessible in every region.

Local actual Next.js page `/car/60600298` was checked with real PostgreSQL data via a temporary read-only SSH adapter, removed before commit. At320/390/639/640/641/767/768/769/1023/1024/1025/1090/1440 CSS px there is no horizontal overflow and the link hit area is44px high. A browser click test confirmed the correct destination opens separately while our car page remains open; the external response was stubbed for this navigation test. Screenshots320/390/1090/1440 and DOM measurements were independently assessed by the required design and responsive reviewers, with no new issues. Reviewers assessed supplied captures rather than independently driving a browser.

Regression checks cover preservation of the listing destination and rejection of mismatched IDs, unrelated hosts, credentials and script URLs. No collector, database schema or photo changes are needed.
