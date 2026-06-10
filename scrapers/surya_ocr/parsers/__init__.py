"""Domain parsers built on the Surya OCR harness.

Each module here applies the generic ``surya_ocr`` harness to ONE document
family, supplying the column semantics + reconciliation rules that family
needs. Keeping them separate from the harness keeps the harness domain-
agnostic and reusable.
"""
