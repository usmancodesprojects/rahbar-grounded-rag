# Corpus

The corpus is drawn from public FAST-NUCES downloads, prospectus, student, admissions and ORIC pages. All nine resources in [the manifest](../corpus/MANIFEST.md) were fetched and verified by SHA-256 on 8 November 2026. The seven PDFs have 279 physical pages. Two HTML documents contain fee and grading data.

| Required property | Source and verification |
| --- | --- |
| At least six documents and forty pages | Undergraduate rules 2023 (26), rules handbook 2026 (58), prospectus rules (5), student handbook (64), annual reports (33 and 85), entrepreneurship policy (8), plus two HTML pages. |
| Two versions of a policy | August 2023 and June 2026 undergraduate rules. The 2023 source is superseded by default. An explicitly dated query can access it. The 2026 prospectus is a separate summary with its own numbering. |
| Image-only scan | All eight pages of the entrepreneurship and start-ups policy have no extractable text. Most of the 2023 rules also lack a usable text layer. Tesseract processes image-bearing pages without text. |
| Informational table | Fee Structure and Grading contain row-aligned tuition and grade-point data. Annual reports contain institutional statistics. |
| Long definitions | The 2026 handbooks contain a generative AI policy with multi-paragraph explanations and examples. |
| Deliberately absent topic | Hostel key replacement deposits and overnight visitor curfew. The transport and hostel prospectus is excluded. Mentions of accommodation do not establish those policies. |
| Exact terms | Rules 1.21 and 3.14, the 2.00 CGPA threshold, grade codes and fee amounts. |

The indexer records one-based physical PDF pages even where the printed pagination differs. HTML counts as one page. Raw downloads and extracted snapshots stay outside Git. Review SHA-256 and version labels together when deliberately updating a source.
