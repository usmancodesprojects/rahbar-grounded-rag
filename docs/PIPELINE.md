# Indexing and querying

The Job extracts pages with PDFium and renders image-bearing pages that lack text for Tesseract. OCR ran on 21 pages of the 2023 undergraduate rules, all eight pages of the entrepreneurship policy, two student handbook pages, and one 2026 academic rules page. The raster has a bounded size, Tesseract uses one OpenMP thread and each OCR call has a 25-second timeout. The indexer records attempted OCR pages and empty outputs by filename and physical page. The snapshot has empty output on physical pages 3–5 of the 2023 rules, 1, 2, 56 and 57 of the 2026 rules, and 2 and 63 of the student handbook. The entrepreneurship policy yielded text on all eight pages.

The HTML fee and grading pages use DOM rows and cells and keep pipe-separated columns, which avoids depending on browser spacing. For example, flattening the fee table to a newline-delimited text stream yields BBA / BS on one line and Rs. 12,000 on the next. The DOM extractor writes `BBA / BS | Rs. 12,000` as one row and keeps empty cells in place. PDF tables use the text-layer reading order and can still lose cell relationships.

Cleaning drops frequently repeated margin lines and standalone margin page numbers. It removes soft hyphens and repairs lowercase line-wrap breaks. It preserves clause identifiers, paragraph breaks, table delimiters and headings. Chunking uses physical pages, then headings and clauses, then paragraph and sentence boundaries. Very long spans fall back to overlapping word windows. Word counts are a reproducible proxy for token counts.

Ollama embeds chunks with `nomic-embed-text:v1.5` at 768 dimensions. The Job and API read the same `EMBED_MODEL` key. The indexer publishes the model, dimension, generation and collection pointer after writing all chunks. Each chunk stores its ID, text and vector along with `source`, `section`, `page`, `doc_version` and `superseded`. The corpus PVC is loaded separately from image builds, so source updates do not require rebuilding the API or indexer image.

The API checks the pin before query embedding, filters superseded passages unless the user explicitly requests an older version, and excludes suspect passages before generation. It validates one JSON response, retries invalid output once and falls back to a canned answer if validation still fails. Displayed lines must quote retrieved evidence. The Redis cache uses cosine similarity and checks scope tokens before reuse. The collection ID namespaces cache entries. A generation update invalidates prior entries immediately.

## Measurement method

`eval/measure.py` extracts the same sources, reuses identical embeddings across chunk configurations and compares the rankings with the frozen golden set. Recall uses unique exact source and section pairs or explicitly supplied chunk IDs. Questions with no relevant passages are excluded from recall and included in abstention. Live evaluation counts structured citations against source, section and page. CI uses the fixture baseline and reports per-question outcomes and citation references. Use `--raw-out` to retain a local transcript for manual review. Production and fixture baselines are separate.

Use the Prometheus cache counters as a ratio with `sum(rate(rahbar_cache_total{result="hit"}[5m])) / sum(rate(rahbar_cache_total[5m]))`. Retrieval and generation timing are separated by stage. Model token histograms use provider token counts. The API logs IDs, similarity scores, provider, cache status and abstention for each answer.


## Chunk and cache tuning

The standalone extraction contained 68,074 whitespace-delimited words. The initial retrieval comparison used exact cosine ranking with the same Nomic model and version predicate as serving.

| Target words | Overlap words | Chunks | Word amplification | Recall@3 | Recall@5 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | 25 | 1,140 | 1.056 | 76.92% | 76.92% |
| 400 | 50 | 1,024 | 1.026 | 76.92% | 76.92% |
| 650 | 80 | 988 | 1.000 | 76.92% | 76.92% |

Recall tied on the first evaluation pass. The 400-word setting reduces duplication versus 200 words while limiting the amount of evidence sent to the model compared with 650. The final historical judgments compare the actual change to clause 6.8 in the 2023 and 2026 sources.

| Cosine threshold | Equivalent hits | False hits |
| ---: | ---: | ---: |
| 0.90 | 2 | 1 |
| 0.92 | 2 | 0 |
| 0.96 | 2 | 0 |

The false hit at 0.90 equated dropping a course with withdrawing from it. Their measured similarity was 0.9042, and the rules distinguish the two actions. Of the tested candidates, 0.92 was the lowest threshold with zero false hits. The sample covers two equivalent pairs and four distinct pairs. The full cache still requires matching numeric, temporal and negation scope.
