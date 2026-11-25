# Equipment status labels — 25 November 2026

Replaced “Штатно” with “В стандартной комплектации” and “Опция” with “Дополнительно — наличие уточняется”. Source symbols ● and ○ retain their meaning; no assumptions about an individual car's optional equipment are added. The existing model-data notice remains.

Each equipment name appears above its status, using white for names and gray for explanations. This avoids narrow status columns on phones.

The actual Next.js page `/car/58649042`, containing both statuses, was tested at320/390/639/640/641/767/768/769/1023/1024/1025/1090/1440 CSS px using real PostgreSQL data via a temporary read-only SSH adapter. Production database code was restored before commit. At all13widths there was no horizontal overflow; all32items kept status below name and inside the viewport. Screenshots320/390/1090/1440 were independently assessed by the required design and responsive reviewers, with no issues. Reviewers assessed supplied screenshots and DOM results rather than running their own interactive browsers.
