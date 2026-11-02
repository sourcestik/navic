# Phase 7 — report, API documentation and viva pack

## Delivered material
- `report.md` and `output/pdf/navic-minor-project-report.pdf`: standard minor-project report with abstract, objectives, literature survey, methodology, design, implementation, actual results, deployment status, limitations, future work and references.
- `openapi.json` and `/docs`: the machine-readable API contract and interactive Swagger UI. Swagger assets need an internet connection; the JSON contract is local.
- `viva-guide.md`: two- and five-minute explanations, source walkthroughs, concept primers, technology choices and weaknesses.
- `viva-questions.md`: 60 questions with model answers and tricky follow-ups across ten categories.
- `demo-script.md`: click-by-click demonstration, expected results and failure recovery.
- `cheat-sheet.md` and `output/pdf/navic-viva-cheat-sheet.pdf`: one-page revision content.
- `screenshots/`: real desktop and mobile/offline browser captures.
- `references.md`: sources and verification record.

The report identifies public deployment as pending. Before final submission, add the actual API/frontend URLs, deployed commit and cloud verification results. Supply your real student/supervisor details and any mandatory institutional certificate or declaration; none have been invented.

## Regenerate the PDFs
Install the optional report dependency in your virtual environment:
```sh
.venv/bin/python -m pip install -r requirements-report.txt
.venv/bin/python scripts/build_report.py
```
The script uses ReportLab and a local Unicode font if available, otherwise ReportLab's bundled Vera. Fonts can affect pagination, so inspect the regenerated PDFs. The delivered files were rendered and visually checked. Keep the cheat sheet to one page.

## Learn and rehearse
Read the short pitch first, trace one request through the source, then work through the concept primers before memorizing answers. Use the question bank to explain assumptions, not to hide gaps. The interactive mock viva starts after the remaining deployment work: one question, your answer, a score out of ten, corrections and a model response. Difficulty increases gradually until you say stop.

## Three-line revision
OpenAPI is the contract; Swagger UI is a tool that displays and executes that contract.
The report records measured evidence and limitations, while the viva pack explains why the design works.
Update deployment evidence before submission and rehearse the local offline fallback.
