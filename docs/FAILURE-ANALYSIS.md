# Failure analysis

The fixture and real corpus are separate. An observed fixture result describes the application path without a real generator. An observed retrieval-only comparison measures evidence ranking without scoring generation.

## A. Extraction

A text-layer-only extraction returned zero non-empty pages out of eight for the entrepreneurship PDF. The OCR-enabled run recovered text on all eight. The 2023 rules also lose most of their usable content. Diagnose the issue with page-level extraction and compare the indexer's `ocr_pages` and `empty_pages` fields against the expected page range. Bounded OCR recovers searchable text where the scan is legible. Report missing pages separately from a zero-recall result.

## B. Chunking

A fixed 100-word split of the 125-word vision and disclaimer block on physical page 4 of the 2026 academic rules cut a sentence spanning words 91–125 after word 100. The shipped structure-aware window kept that sentence together. To diagnose a similar error, compare the original page and the retrieved passage before increasing top-k. The indexing log gives the physical page and the retrieval log gives the chunk ID.

## C. Retrieval

The live fixture experiment lowered the fixture stack's top-k to one. The injection query ranks a poisoned chunk ahead of its relevant attendance section. The API still declines the injection, while retrieval loses the correct source and the recall gate rejected the run. Recall@5 fell from 100% to 83.33%. Check `chunk_ids`, `scores` and the recall breakdown. Restore the configured top five and preserve the same baseline. The embedding pin provides a separate hard failure for mismatched vector spaces.

## E. Source version

For the undated fixture attendance question, the unfiltered cosine ranking placed the superseded 2023 passage first at 0.298 and the 2026 passage second at 0.270. The default metadata filter removes the 2023 passage, so the fixture response cites 2026. The explicitly dated 2023 question still retrieves the old edition. A likely symptom in production is a well-formed citation with the wrong publication year. Compare retrieved source names and inspect `doc_version` and `superseded` before tuning the model.
