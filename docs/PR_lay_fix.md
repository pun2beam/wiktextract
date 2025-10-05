Title
-----
REST example breadcrumb enforcement default-on for "lay" regression

Summary
-------
- Default the REST parser's strict sense-boundary matching to on via `WIKTEXTRACT_STRICT_SENSE_BOUNDARY` while retaining a fallback guard.
- Extend `tools/repro_lay.py` to fetch live REST HTML for arbitrary titles and accept fixture overrides for the "before" reproduction.
- Add a helper report to quantify part-of-speech changes for targeted example texts across boundary toggle runs.

Root cause
----------
- REST extraction previously fell back to the most recent sense when breadcrumb matching failed, which allowed the "pullet" citation to drift into the noun section when the guard was disabled.
- The strict matching logic landed behind a flag and the reproduction script only handled the bespoke "lay" fixture, preventing wider smoke checks.

Fix
----
- Normalize the strict-boundary environment flag handling and ensure the guard is enabled by default unless explicitly switched off.
- Broaden the reproduction script with word selection, live REST fetching, and fixture overrides so we can validate both the patched and legacy behaviours.
- Provide an automated comparison report that counts example POS changes for a curated word list across pre/post runs.

Testing
-------
- `PYTHONPATH=src python tools/repro_lay.py --out-a outA.jsonl --out-b outB.jsonl --contains "I never kill a pullet"`
- `PYTHONPATH=src python tools/compare_jsonl_examples.py --a outA.jsonl --b outB.jsonl --contains "I never kill a pullet"`
- `PYTHONPATH=src python tools/inspect_jsonl.py --jsonl outB.jsonl --word lay | head -n 60`
- `WIKTEXTRACT_STRICT_SENSE_BOUNDARY=0 PYTHONPATH=src python tools/repro_lay.py --out-a outA_off.jsonl --out-b outB_off.jsonl --contains "I never kill a pullet"`
- `WIKTEXTRACT_STRICT_SENSE_BOUNDARY=0 PYTHONPATH=src python tools/compare_jsonl_examples.py --a outA_off.jsonl --b outB_off.jsonl --contains "I never kill a pullet"`
- `WIKTEXTRACT_STRICT_SENSE_BOUNDARY=0 PYTHONPATH=src python tools/inspect_jsonl.py --jsonl outB_off.jsonl --word lay | head -n 60`
- `PYTHONPATH=src python tools/report_pos_changes.py --old old/merged.jsonl --new new/merged.jsonl --words words.txt`

Risk/Impact
-----------
- Low: the stricter default only affects example attachment when breadcrumbs disagree, and the toggle plus smoke report cover multi-POS regressions.

変更ファイル
------------
- src/wiktextract/rest_parser.py
- tools/repro_lay.py
- tools/report_pos_changes.py
- docs/PR_lay_fix.md

POS change summary
-------------------
```
Word         Changed   OldUnique   NewUnique
--------------------------------------------
set                0           0           0
run                0           0           0
lie                0           0           0
lead               0           0           0
fast               0           0           0
fair               0           0           0
lay                1           1           1
```
