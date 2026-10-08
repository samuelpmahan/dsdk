## Latest
- Branch `main` (only remote branch on disk). Last commit 2025-07-23, Samuel Mahan: "in find_bridge_articles, set default similarity_threshold to 0.1". This is stale, about 14 months old.

## Purpose
A Scrapy spider over the Stanford Encyclopedia of Philosophy (plato.stanford.edu) plus offline feature engineering: TF-IDF keyword fingerprints, citation-based communities, and "bridge" articles that connect communities through shared concepts. Outputs are CSVs of articles.

## Stack
Python: Scrapy (`scrapy.cfg`, `scrapy_sep/`), pandas, `requirements.txt`. Optional spaCy in `feature_engineer.py`, with a no-spaCy variant in `fe_no_spacy.py`. Data is held in CSVs.

## Key modules
- `/home/user/samuelpmahan/sep-scrape/scrapy_sep/spiders/sep-spider.py` — `SepSpider`: full or incremental scrape, reading URLs from `sep_articles.csv`.
- `/home/user/samuelpmahan/sep-scrape/feature_engineer.py` — `calculate_tfidf_fingerprints`, `build_citation_communities`, `extract_entities_and_concepts`, `find_bridge_articles` (default threshold 0.2).
- `/home/user/samuelpmahan/sep-scrape/fe_no_spacy.py` — the same pipeline without spaCy (default threshold 0.1).
- `/home/user/samuelpmahan/sep-scrape/sep_articles.csv` — scraped article table.

## Reusable for dsdk
- C1 — `/home/user/samuelpmahan/sep-scrape/fe_no_spacy.py` — `calculate_tfidf_fingerprints`: top-N keyword fingerprints per article, dependency-light text-mining baseline.
- C2 — `/home/user/samuelpmahan/sep-scrape/fe_no_spacy.py` — `build_citation_communities` and `find_bridge_articles`: community bridging over a link graph.

## Evidence quality
- Low. No tests and no evaluation of bridge quality. The two feature scripts disagree on the default threshold (0.2 vs 0.1). Not run.

## Open questions
- Which of the two pipelines produced the committed outputs?
- Is the 0.1 bridge threshold validated against any labeled data?
- Does reuse of `sep_articles.csv` match SEP's terms of use? Not checked.
