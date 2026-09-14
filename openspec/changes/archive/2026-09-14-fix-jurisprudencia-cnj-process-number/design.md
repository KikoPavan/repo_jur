# Design: Fix Jurisprudencia CNJ Process Number

## Architecture

Single-module change inside `src/pipeline_juridico/legal_semantic_review.py`,
in the `_deterministic_extract` function's Jurisprudencia/Processo block
(current lines ~299-334). No new module is required; a small pure helper
function is added and unit-tested directly.

```
_deterministic_extract(body, ...)
  └── _resolve_cnj_processo_numero(pages) -> str | None   # NEW
        ├── _cnj_checksum_valid(cnj_20_digits: str) -> bool   # NEW
        ├── scan punctuated CNJ matches, validate, normalize (no-op, already canonical)
        ├── scan standalone 20-digit tokens, validate, normalize to canonical form
        ├── dedupe by canonical form across the whole document
        └── return sole candidate, or None if 0 or >1 distinct candidates
```

The two now-removed regexes (`appellate_match`, STJ register-number
`reg_match`) are deleted entirely from the `repo_jur_processo_numero`
resolution path. They are not reused anywhere else in the codebase for this
field (`search_files` confirms the only other `processo_numero` references
are field-name plumbing in `config.py`, `legal_producer.py`,
`legal_segment_identity.py`, `retrieval/index.py` — none re-implement this
regex).

## CNJ Checksum Algorithm (mod 97, ISO 7064-style, ENunciado CNJ)

Canonical form: `NNNNNNN-DD.AAAA.J.TR.OOOO` (7 sequential digits, 2 check
digits, 4-digit year, 1-digit judicial segment `J`, 2-digit court `TR`,
4-digit origin unit `OOOO` — 20 significant digits total).

Given the 20 digits as `SEQ(7) DV(2) YEAR(4) SEG(1) COURT(2) ORIGIN(4)`:

```python
def _cnj_checksum_valid(digits20: str) -> bool:
    if len(digits20) != 20 or not digits20.isdigit():
        return False
    seq, dv, year, seg, court, origin = (
        digits20[0:7], digits20[7:9], digits20[9:13],
        digits20[13:14], digits20[14:16], digits20[16:20],
    )
    base = int(seq + year + seg + court + origin + "00")
    expected_dv = 98 - (base % 97)
    return f"{expected_dv:02d}" == dv
```

Verified against the real fixtures during investigation:
- `0311049092016824001850001` (AIRESP `Número de Origem` line) contains the
  standalone 20-digit token `03110490920168240018`, whose computed DV is
  `09`, matching digits 8-9 → **valid**, canonical
  `0311049-09.2016.8.24.0018`.
- The other digit runs on the same line (`0311049092016824001850001` at 25
  digits, `311049092016824001850001` at 24 digits,
  `3110490920168240018` at 19 digits) are **not** standalone 20-digit tokens
  (wrong length after boundary anchoring) and are excluded by construction —
  they are truncation/padding artifacts of the same source number, not
  independent candidates.

## Token Scanning Rule

Only tokens matching `(?<!\d)\d{20}(?!\d)` (exactly 20 digits, not
preceded/followed by another digit) are considered 20-digit CNJ candidates.
This avoids the failure mode of sliding a 20-digit window across a longer
digit run and generating spurious overlapping candidates from padding
variants of the same real number (e.g. the AIRESP line's 25-digit and
24-digit variants must never each spawn multiple 20-digit sub-windows).

## Multi-Origin Ambiguity — Confirmed Impact on Existing Golden Fixtures

Both `tests/test_conformance/golden/REsp_1704551-SP.md` and
`AINTARESP_1462304-PA.md` carry an STJ "Número(s) Origem" line listing
**multiple** distinct, independently checksum-valid 20-digit CNJ tokens
(STJ certidão headers list one origin-CNJ per instance the process passed
through, not a single canonical number):

- REsp_1704551-SP: `00134589020148260100` and `22019934120158260000` — both
  checksum-valid, structurally distinct.
- AINTARESP_1462304-PA: `00277367120134010000` and `00386267720114013900` —
  both checksum-valid, structurally distinct.

Under the corrected rule (Objective 5 of `proposal.md`), neither fixture has
a deterministic way to prefer one origin-CNJ as "the" process number — this
is a genuine irreducible ambiguity, not a defect in the checksum logic. Per
the fail-closed rule, `repo_jur_processo_numero` is **not extracted** for
either fixture under the corrected implementation.

This is a deliberate, expected behavior change from today's incorrect
appellate-header fallback (which is exactly the defect class this change
fixes — see the AIRESP real-world case). The existing conformance
assertions at `tests/test_conformance/test_metadata_contract.py:122-124` and
`:154-155` (`assert "1.704.551" in proc_field.value`, `assert "1462304" in
proc_field.value`) encode the old, incorrect contract and MUST be updated
as part of this change to assert the corrected behavior (field not present,
or present only if the implementer finds — after literal, careful reading —
that one of the two origin numbers is unambiguously the record's own current
process by some other deterministic signal; if no such signal exists, the
task is to update the assertion to `"repo_jur_processo_numero" not in
extracted_names` for these two fixtures). No fabricated disambiguation rule
is to be invented to force these two fixtures to keep resolving a value.

`tests/test_conformance/test_conformance.py` (the `@pytest.mark.conformance`
real-corpus suite) must also be checked for any assertion on
`repo_jur_processo_numero` derived from these two PDFs; update identically
if found.

## Legal OKF Profile Spec Clarification

`openspec/specs/legal-knowledge/spec.md`'s `repo_jur_processo_numero`
requirement currently reads (line 255):

> `repo_jur_processo_numero` (String, Mandatory): The process identifier
> (CNJ format is preferentially preferred, but STJ/STF appellate case
> identifiers like REsp/AREsp/AgInt or register numbers are also valid
> fallbacks when CNJ is not available; no separate field for court-class
> identifiers exists in the FROZEN profile).

This delta change's `MODIFIED Requirements` block replaces that fallback
language: STJ/STF appellate case identifiers and internal register numbers
are no longer valid values for this field under any circumstance — the field
is either a checksum-valid CNJ (verbatim or normalized from an unpunctuated
20-digit source token) or is not extracted. This also updates the mandatory
field-presence contract: `repo_jur_processo_numero` remains Mandatory for
publication (per `legal_producer.py`'s existing `validate_candidate`
mandatory-field check for `Jurisprudencia`), so a document with no
checksum-valid CNJ anywhere continues to be blocked as `review_required` at
the Producer boundary — this is existing, unmodified behavior
(`legal_producer.py:491-494`); this change does not alter that gate, it only
prevents an invalid value from ever reaching it.

## Risks and Mitigations

- **Risk**: Deleting the appellate-header/register-number fallback could
  reduce automatic extraction rate for the corpus, pushing more documents
  into `review_required`. **Mitigation**: this is the correct, intended
  outcome — an incorrect canonical field value is strictly worse than a
  human review gate; explicitly endorsed by Objectives 3, 5, 6.
- **Risk**: A false-negative checksum bug could reject a genuinely valid CNJ.
  **Mitigation**: the algorithm is the standard published CNJ mod-97 rule;
  unit tests pin exact expected DV values for both the canonical example
  (`0311049-09.2016.8.24.0018`) and a deliberately invalid DV case.
- **Risk**: golden fixture updates could mask a real regression instead of
  reflecting the intended contract change. **Mitigation**: `tasks.md`
  requires citing the specific line diff and checksum computation for each
  updated assertion, not a blanket relaxation.

## CLI / Runtime Interface

No CLI surface change. `converter-juridico` / `repo-jur producer build`
invocation and flags are unchanged.
