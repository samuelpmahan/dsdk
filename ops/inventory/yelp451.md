## Latest
- Branch `master` (only remote branch on disk). Last commit 2018-04-24, Jared Goodwin: "Fixed filter by brunch not working due to stray single quote". This is a 2018 course artifact with no later activity.

## Purpose
A 2018 Team 37 course project: a PostgreSQL schema for a Yelp-style business/review/user/check-in dataset (the table names and row counts suggest the Yelp academic dataset), with aggregate-maintaining triggers, backfill SQL, and a C# WPF desktop browser for businesses and check-in charts. The dataset rows are not in the repo, only the schema and row-count notes.

## Stack
PostgreSQL with PL/pgSQL triggers; C# .NET Framework WPF app using Npgsql 3.1.9, WPFToolkit 3.5 and DataVisualization; a Visual Studio solution with build outputs (`bin/`, `obj/`, `.vs/`) committed.

## Key modules
- `/home/user/benhamlin314/yelp451/team37_DDL.sql` — schema: business, review, user, checkin, business category/attribute, hours_open, and friendship (edge list `friend1_id`, `friend2_id`).
- `/home/user/benhamlin314/yelp451/Team_37_TRIGGER.sql` — AddReviewCount, AddReviewRating, and CheckIn triggers, plus manual insert/select/delete tests.
- `/home/user/benhamlin314/yelp451/team37_UPDATE.sql` — backfill of num_checkins, review_count, and review_rating.
- `/home/user/benhamlin314/yelp451/team37_TableSizes.txt` — row counts per table.
- `/home/user/benhamlin314/yelp451/Team-37_Mile2_UI/Team-37_Mile2/Team-37_Mile2/MainWindow.xaml.cs` — cascading state, city, postal code, and category filters; search SQL built by string concatenation.
- `/home/user/benhamlin314/yelp451/Team-37_Mile2_UI/Team-37_Mile2/Team-37_Mile2/GraphWindow.xaml.cs` — check-in chart binding (`SetChart`).
- `/home/user/benhamlin314/yelp451/Team-37_Mile2_UI/Team-37_Mile2/Team-37_Mile2/TableWindow.xaml.cs` — results table window.

## Reusable for dsdk
- C2 — `/home/user/benhamlin314/yelp451/team37_DDL.sql` (friendship_table) — a user-user friendship edge list of about 1.05M rows per the table sizes; a graph-mining input shape. The data itself is not in this repo.
- B1 — `/home/user/benhamlin314/yelp451/team37_TableSizes.txt` — per-table row counts; a sanity baseline for ingestion checks.
- B1 — `/home/user/benhamlin314/yelp451/team37_UPDATE.sql` — recomputes derived aggregates from base tables; a pattern for rebuilding derived columns.

## Evidence quality
- Low. The "tests" are manual INSERT/SELECT/DELETE scripts with no assertions. The WPF app has no test project.
- Confirmed defect: `update_rating()` in `Team_37_TRIGGER.sql` sets `review_rating` to `(SELECT AVG(stars) FROM review_table)` with no business filter. Each insert therefore overwrites that business's rating with a global average. `team37_UPDATE.sql` computes the per-business average, so the trigger and the backfill disagree.
- `MainWindow.xaml.cs` concatenates user-selected values into SQL, which is an injection risk.
- `Team-37_ER.pdf` was not extracted and was not evaluated.

## Open questions
- What is the source and license of the Yelp data? Confirm before reusing any row-level data.
- Is the trigger bug fixed on any other branch? Only `master` is on disk.
- Is `Team-37_ER.pdf` the authoritative ER model? Not read.
