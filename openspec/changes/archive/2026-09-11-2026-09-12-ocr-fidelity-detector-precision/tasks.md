# Tasks: OCR Fidelity Detector Precision and Privacy Correction

- [x] T1: Audit and clean canonical specs (remove `double_checked`, `[[ilegível]]`)
- [x] T2: Update `models.py` to remove `fingerprint` and add privacy-safe fields (`issue_id`, related offsets)
- [x] T3: Implement privacy-safe report generation in `fidelity.py` and `report.py`
- [x] T4: Refine Duplication Detector (handle ESCRITURA4 scenarios)
- [x] T5: Refine Entity Inconsistency Detector (handle lexical variants and context)
- [x] T6: Refine Visual Uncertainty Detector (handle structured codes)
- [x] T7: Update Quality Gate to validate the new report contract
- [x] T8: Create synthetic fixtures and run conformance/regression tests
- [x] T9: Final verification and archive reconciliation
