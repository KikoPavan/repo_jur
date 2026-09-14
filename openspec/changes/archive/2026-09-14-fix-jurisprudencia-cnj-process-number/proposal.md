# Proposal: Fix Jurisprudencia CNJ Process Number

## Why

Real-corpus regression (`output/AIRESP-1833684-2020-02-12.md`, produced from
`input/AIRESP-1833684-2020-02-12.pdf`) shows the Producer writing:

```
repo_jur_processo_numero: AgInt no RECURSO ESPECIAL Nº 1833684 - SC
```

Root cause: `src/pipeline_juridico/legal_semantic_review.py:299-334`
(`_deterministic_extract`) resolves `repo_jur_processo_numero` in three
ordered fallback tiers:

1. a strict CNJ regex (`\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`) — requires the
   punctuation already present in the source text;
2. an "appellate case identifier" regex matching STJ/STF recursal headers
   (`AgInt`, `REsp`, `AREsp`, `RE`, `ADI`, ... + free-form number);
3. an internal STJ register-number fallback (`NNNN/NNNNNNN-N`).

For `AIRESP-1833684-2020-02-12.md` tier 1 finds nothing because the source
page never prints the CNJ with its canonical punctuation — it only appears as
a raw, unpunctuated digit run under the heading `Número de Origem:`
(`... 03110490920168240018 ...`, among several padded/truncated variants on
the same line). Because tier 1 fails, tier 2 fires and matches the record's
own recursal header `AgInt no RECURSO ESPECIAL Nº 1833684 - SC`, which the
current code accepts as `repo_jur_processo_numero` even though it is the
identifier of the **appellate recourse itself**, not the CNJ number of the
underlying judicial process.

This violates the current Legal OKF Profile
(`openspec/specs/legal-knowledge/spec.md`, `repo_jur_processo_numero`
requirement), which defines the field as the process identifier and — per
the field's own controlling text — treats CNJ format as the preferred,
canonical representation; a recursal-class label with a recourse number is
not a process identifier and must never populate this field once a CNJ is
verifiably reconstructible, and must never populate it as a bare fallback
when doing so requires accepting a non-CNJ, non-process-identity string
(court-class + recourse number, or an internal STJ/STF register number) in
place of the process number.

Deterministic reconstruction of the AIRESP source: the `Número de Origem:`
line contains multiple digit runs derived from the same underlying case
number via truncation/padding artifacts of the source scan
(`0311049092016824001850001`, `311049092016824001850001`,
`03110490920168240018`, `3110490920168240018`). Scanning every standalone
20-digit token on that line and validating it against the CNJ mod-97 check
digit algorithm (NNNNNNN·AAAA·J·TR·OOOO, DV = 98 − ((base·100) mod 97))
yields **exactly one** structurally valid 20-digit CNJ candidate:
`03110490920168240018`, whose check digits (`09`) match position 8-9,
confirming the canonical form `0311049-09.2016.8.24.0018`. No other 20-digit
substring on that line passes the checksum. This is not assumed — it is
verified by the same deterministic checksum rule this change implements.

## What Changes

Replace the current 3-tier fallback (CNJ punctuated → appellate header →
internal register number) with a checksum-validated, fail-closed CNJ
resolution: scan the whole document for punctuated and standalone 20-digit
CNJ candidates, validate each against the CNJ mod-97 check-digit algorithm,
and populate `repo_jur_processo_numero` only when exactly one distinct
checksum-valid CNJ is found — never falling back to an appellate/recursal
header or an internal STJ/STF register number. See `## Proposed Behavior`
below for the full resolution algorithm and `## Objectives` for the
normative constraints this change enforces.

## Objectives

1. `repo_jur_processo_numero` accepts only a value that is, or is
   deterministically derivable from, a checksum-valid CNJ number in the
   canonical `NNNNNNNN-DD.AAAA.J.TR.OOOO` format (7-2-4-1-2-4 digit groups).
2. Unpunctuated 20-digit CNJ candidates found in the source text are
   normalized to the canonical punctuated form only after their check
   digits validate under the CNJ mod-97 algorithm.
3. A record's own appellate/recursal header (class + recourse number, e.g.
   `AgInt no RECURSO ESPECIAL Nº 1833684 - SC`) and internal STJ/STF register
   numbers (e.g. `2019/0251395-0`) are permanently removed as acceptable
   values or fallbacks for `repo_jur_processo_numero`.
4. When two or more structurally distinct, checksum-valid CNJ candidates
   are found with no deterministic way to identify which is the record's
   own base process, extraction fails closed (field left unresolved), never
   guesses.
5. When no checksum-valid CNJ is recoverable at all, `repo_jur_processo_numero`
   is left unresolved — never backfilled with the appellate/register number.

## Scope

In scope: `legal_semantic_review.py` process-number extraction only
(the `_deterministic_extract` fallback chain feeding
`repo_jur_processo_numero`), its dedicated tests, and this profile
clarification in `openspec/specs/legal-knowledge/spec.md`.

Out of scope (explicitly deferred, not implemented by this change):
- `repo_jur_recurso_classe`, `repo_jur_recurso_numero`,
  `repo_jur_data_publicacao` — possible future profile fields.
- Any change to `repo_jur_tribunal`, `repo_jur_relator`,
  `repo_jur_data_julgamento` extraction logic.
- Any change to `legal_segment_identity.py` beyond what is inherited for
  free by reusing the corrected extractor (it already imports
  `_deterministic_extract`; no separate identity-resolution logic change is
  planned).
- Publishing/archiving/committing; no `bundle/` file is touched by this
  change.

## Proposed Behavior

Replace the current 3-tier fallback (CNJ punctuated → appellate header →
internal register number) with:

1. Scan all pages for punctuated CNJ matches
   (`\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`); validate each against the CNJ
   check-digit algorithm; discard invalid matches.
2. Scan all pages for standalone 20-digit tokens (`(?<!\d)\d{20}(?!\d)`);
   validate each against the same algorithm; normalize valid ones to
   canonical punctuated form.
3. Union all checksum-valid CNJ candidates (steps 1+2) across the document,
   deduplicated by their canonical normalized form.
4. If exactly one distinct valid CNJ remains: it is `repo_jur_processo_numero`.
5. If zero valid CNJ remain: `repo_jur_processo_numero` is not extracted
   (field absent) — no fallback to appellate header or register number.
6. If two or more structurally distinct valid CNJs remain with no
   deterministic rule to prefer one (this change introduces none): treat as
   ambiguous — field is not extracted (fail-closed, matching the existing
   `AMBIGUOUS`/absence pattern used elsewhere in this codebase, e.g.
   `legal_segment_identity.py`'s `conflicting_identity_field` handling).

The appellate-header regex and the internal-register regex are deleted from
the `repo_jur_processo_numero` resolution path entirely (not merely
deprioritized) — per Objective 3, they must never populate this field.

## Success Criteria

- New unit tests (RED first, see `tasks.md`) cover: canonical CNJ preserved;
  unpunctuated 20-digit CNJ normalized only when checksum-valid; CNJ chosen
  over a co-present appellate header; appellate header alone yields no
  value; internal register number alone yields no value; two conflicting
  CNJs yield no value (fail-closed); checksum-invalid CNJ-shaped text is
  rejected; unrelated Jurisprudencia metadata fields are unaffected.
- Full `pytest` suite passes with no regressions beyond the two intentionally
  changed conformance fixtures noted in `tasks.md` (REsp/AINT golden fixtures
  whose `Números Origem` lines each happen to contain more than one
  checksum-valid CNJ token unrelated to the record's own process — see
  `design.md` for the exact handling).
- Real-corpus re-run of
  `uv run repo-jur producer build "output/AIRESP-1833684-2020-02-12.md" ...`
  produces `repo_jur_processo_numero: 0311049-09.2016.8.24.0018` (or leaves
  the field absent with a `review_required` block, if implementation
  determines the AIRESP source is itself ambiguous per rule 6 — to be
  confirmed empirically before claiming success, not assumed).
- `openspec validate fix-jurisprudencia-cnj-process-number --strict` and
  `openspec validate --all --strict` pass.
